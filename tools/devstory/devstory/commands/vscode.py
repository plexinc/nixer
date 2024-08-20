import json
import os
import platform
import subprocess as sp
from pathlib import Path
from typing import Tuple

import click

from devstory import output
from devstory.common import (
  CommandResult,
  current_context,
  get_project_dir,
  get_toolchain_files,
  get_toolchain_path,
  get_wrapper_path,
  is_cmake_deps,
  using_new_toolchain,
)
from devstory.common.config import DsConfig


def clang_resource_dir():
  from subprocess import check_output
  from sys import executable

  if not using_new_toolchain():
    wrapper = get_wrapper_path()
    cmd = [executable, str(wrapper)]
  else:
    cmd = ["plexec"]

  cmd.extend(["clang", "--print-resource-dir"])
  rdata = check_output(cmd)
  return Path(rdata.decode("utf-8").rstrip())


def get_new_settings(indexer, cmake_options):
  from click import get_current_context

  ctx = get_current_context().obj
  if using_new_toolchain():
    toolsdir = get_toolchain_path() / "bin"
  else:
    toolsdir = (ctx.home / "tools").resolve()
  project_dir = get_project_dir()

  def make_relative(path: Path):
    if using_new_toolchain():
      return str(path)
    relpath = path.relative_to(project_dir)
    return f"${{workspaceFolder}}{os.sep}{relpath}"

  common_settings = {
    "cmake.cmakePath": make_relative(toolsdir / "cmake"),
    "cmake.generator": "Ninja",
    "cmake.configureSettings": dict(item.split("=") for item in cmake_options),
  }
  if not is_cmake_deps():
    common_settings["cmake.cacheInit"] = str(
      (ctx.home / "initial-cache.cmake").relative_to(project_dir)
    )

  # Settings that turn off each indexer
  turn_off = {
    "ccls": {
      "ccls.launch.command": "Disabled",
    },
    "clangd": {
      "clangd.path": "Disabled",
    },
    "microsoft": {
      "C_Cpp.autocomplete": "Disabled",
      "C_Cpp.dimInactiveRegions": False,
      "C_Cpp.default.cppStandard": "c++14",
      "C_Cpp.errorSquiggles": "Disabled",
      "C_Cpp.formatting": "Disabled",
      "C_Cpp.intelliSenseEngine": "Disabled",
      "C_Cpp.intelliSenseEngineFallback": "Disabled",
    },
  }

  ds_ctx = current_context()
  indexer_settings = {
    "ccls": {
      "ccls.cache.directory": f"${{workspaceFolder}}{os.sep}.ccls-cache",
      "ccls.launch.command": make_relative(toolsdir / "ccls"),
      "ccls.misc.compilationDatabaseDirectory": make_relative(ctx.home),
      "ccls.completion.enableSnippetInsertion": True,
      # This excludes the msvc precompiled headers - turn them on again when we have
      # clang-cl on Windows
      "ccls.clang.excludeArgs": ["/YcC:*", "/YuC:*", "/FIC:*", "/FpC:*"],
      "ccls.clang.resourceDir": str(clang_resource_dir()),
      "ccls.highlight.function.face": ["enabled"],
      "ccls.highlight.variable.face": ["enabled"],
      "ccls.highlight.type.face": ["enabled"],
      **turn_off["clangd"],
      **turn_off["microsoft"],
    },
    "clangd": {
      "clangd.path": str(toolsdir / "clangd"),
      "clangd.arguments": [
        f"--query-driver={toolsdir}{os.path.sep}*clang*",
        "-pch-storage=memory",
        f"-compile-commands-dir={str(ctx.home)}",
      ],
      **turn_off["ccls"],
      **turn_off["microsoft"],
    },
    "microsoft": {
      "C_Cpp.autocomplete": "Default",
      "C_Cpp.dimInactiveRegions": True,
      "C_Cpp.default.cppStandard": "c++17",
      "C_Cpp.errorSquiggles": "Disabled",
      "C_Cpp.formatting": "Disabled",
      "C_Cpp.intelliSenseEngine": "Default",
      "C_Cpp.default.intelliSenseMode": "msvc-x64",
      "C_Cpp.intelliSenseEngineFallback": "Disabled",
      "C_Cpp.default.compileCommands": f"{str(ds_ctx.home / 'compile_commands.json')}",
      **turn_off["ccls"],
      **turn_off["clangd"],
    },
    "none": {
      **turn_off["ccls"],
      **turn_off["clangd"],
      **turn_off["microsoft"],
    },
  }

  settings = common_settings
  settings.update(indexer_settings[indexer])

  return settings


def create_cmake_variants():
  plex_dev = DsConfig.load_plex_dev()
  project_variants = plex_dev.load_list_setting(
    "project", "variants", ["standard", "nano"]
  )
  variant_key = plex_dev.load_setting(
    "project", "variant_key", "PLEX_MEDIA_SERVER_VARIATION"
  )

  choices = {}
  for variant in project_variants:
    choices[variant] = {
      "short": variant.title(),
      "long": f"Build the {variant} variant",
      "settings": {variant_key: variant},
    }

  variants = {
    "buildType": {
      "default": "debug",
      "description": "Debug builds",
      "choices": {
        "debug": {
          "short": "Debug",
          "long": "Build with debug information",
          "buildType": "Debug",
        },
        "relwithdebinfo": {
          "short": "RelWithDebInfo",
          "long": "Build release with debug info",
          "buildType": "RelWithDebInfo",
        },
      },
    },
    "variant": {
      "default": project_variants[0],
      "description": "Project variant to build",
      "choices": choices,
    },
  }

  variant_file = get_project_dir() / ".vscode" / "cmake-variants.json"
  with variant_file.open("w") as odata:
    json.dump(variants, odata, indent=2)

  return True


def find_visual_studio():
  instance = None

  # We need to find the Visual Studio installations to correctly generate the kits
  prgfiles = Path(os.environ.get("ProgramFiles(x86)", "c:\\Program Files (x86)\\"))
  vswhere = prgfiles / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
  if not vswhere.is_file():
    output.error(
      f"Failed to find vswhere.exe in {vswhere} - make sure you have Visual Studio 2019 installed!"
    )
    return False

  proc = sp.run(
    [
      str(vswhere),
      "-all",
      "-products",
      "*",
      "-format",
      "json",
      "-version",
      "[16.0,17.0)",
    ],
    stdout=sp.PIPE,
  )

  if proc.returncode != 0:
    output.error("Failed to run vswhere!")
    return False

  jsondata = json.loads(proc.stdout.decode())
  for inst in jsondata:
    if not instance:
      instance = inst
      continue

    if instance and inst["productId"] == "Microsoft.VisualStudio.Product.Community":
      instance = inst

  return instance


TOOLCHAIN_TO_VSARCH = {
  "i686-windows-msvc": "amd64_x86",
  "x86_64-windows-msvc": "x64",
  "i686-windows-clang": "amd64_x86",
  "x86_64-windows-clang": "x64",
}


def create_cmake_kits():
  toolchains = get_toolchain_files()

  vsinstance = None
  if platform.system() == "Windows":
    vsinstance = find_visual_studio()
    if not vsinstance:
      output.error("Failed to find a Visual Studio 2019 installation!")
      return False
    output.info(f"Found visual studio in: {vsinstance['installationPath']}")

  kits = []
  for toolchain in toolchains:
    if "cygwin" in toolchain.name:
      continue
    kit = {"name": f"Plex - {toolchain.stem}", "toolchainFile": str(toolchain)}

    if vsinstance:
      kit["visualStudio"] = vsinstance["instanceId"]
      if not toolchain.stem in TOOLCHAIN_TO_VSARCH:
        output.error(f"Missing {toolchain.stem} in TOOLCHAINS_TO_VSARCH!")
        return False
      kit["visualStudioArchitecture"] = TOOLCHAIN_TO_VSARCH[toolchain.stem]

    kits.append(kit)

  kit_file = get_project_dir() / ".vscode" / "cmake-kits.json"
  with kit_file.open("w") as odata:
    json.dump(kits, odata, indent=2)

  return True


def edit_vscode_settings(
  indexer, cmake_options, force_settings
):  # pylint: disable=unused-argument
  settings_file = get_project_dir() / ".vscode" / "settings.json"

  new_settings = get_new_settings(indexer, cmake_options)
  current_settings = {}
  if settings_file.is_file():
    with open(settings_file, "r") as sdata:
      try:
        current_settings = json.load(sdata)
      except json.decoder.JSONDecodeError:
        output.warn(f"Failed to load {settings_file} - will not edit the file")
        output.warn("Here are the values devstory wanted to add: ")
        print(json.dumps(new_settings, indent=2))
        return

  new_settings = get_new_settings(indexer, cmake_options)
  current_settings.update(new_settings)

  settings_file.parent.mkdir(exist_ok=True, parents=True)

  if settings_file.is_file():
    from shutil import copy2

    copy2(settings_file, settings_file.parent / "settings.json.ds_bak")

  with settings_file.open("w") as odata:
    json.dump(current_settings, odata, indent=2)


def do_vscode(
  default: bool,
  cmake_options: Tuple[str],  # list of "key=value" strings
  indexer: str,
  force_settings: bool,
  conan_options: Tuple[str],  # list of "key=value" strings
):
  from devstory.commands.install import do_install

  cmake_options = list(cmake_options)

  ctx = click.get_current_context()
  results = ctx.invoke(
    do_install,
    build="never",
    build_type=None,
    profile=None,
    variation=None,
    debug_deps=None,
    update=False,
    default=default,
    conan_options=conan_options,
  )

  if results != CommandResult.Success:
    return results

  if is_cmake_deps() and not using_new_toolchain():
    ds_ctx = current_context()
    cmake_options.append(f"PROFILE_ID={ds_ctx.profile.env['PLEX_PACKAGE_TARGET']}")
    cmake_options.append(f"PLEX_MEDIA_SERVER_VARIATION={ds_ctx.variation}")
  elif using_new_toolchain():
    toolchain = f"{get_toolchain_path()}{os.path.sep}bin".replace("\\", "/")
    cmake_options.append(f"CMAKE_PROGRAM_PATH={toolchain}")

  if not indexer:
    # For now we set none as the windows indexer,
    # update this when we can use clangd.
    #
    if platform.system() != "Windows":
      indexer = "clangd"
    else:
      indexer = "none"

  output.info(f"Using C/C++ code indexer: {indexer}")

  edit_vscode_settings(indexer, cmake_options, force_settings)

  if using_new_toolchain():
    if not create_cmake_kits():
      return CommandResult.Error
    if not create_cmake_variants():
      return CommandResult.Error

  return CommandResult.Success
