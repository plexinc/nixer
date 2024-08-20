import click

from devstory import output
from devstory.common import (
  CommandResult,
  current_context,
  run_cmake,
  default_profile,
)

MSVC_VERSION_MAP = {
  "14": "2015",
  "15": "2017",
  "16": "2019",
}

MSVC_ARCH_MAP = {
  "x86": "Win32",
  "x86_64": "x64",
  "armv7": "ARM",
  "aarch64": "ARM64",
}


def _get_generator(version):
  return f"Visual Studio {version} {MSVC_VERSION_MAP[version]}"


def do_msvc():
  from devstory.commands.install import do_install

  dsctx = current_context()
  ctx = click.get_current_context()
  results = ctx.invoke(
    do_install,
    build="never",
    build_type=None,
    profile=None,
    variation=None,
    debug_deps=None,
    update=False,
    conan_options=dsctx.stored_flags["conan_options"],
    default=dsctx.stored_flags["default"],
  )

  if results != CommandResult.Success:
    return results

  profile = default_profile()

  output.info(f"Using profile: {profile.name}")
  if not profile.data["settings"]["compiler"] == "Visual Studio":
    output.error("Selected profile is not a Visual Studio profile!")
    return CommandResult.Error

  msvc_version = profile.data["settings"]["compiler.version"]
  msvc_arch = profile.data["settings"]["arch"]
  msvc_generator = _get_generator(msvc_version)
  output.info(
    f"MSVC - version: {msvc_version} arch: {msvc_arch} generator: {msvc_generator}"
  )

  if "cmake_options" in dsctx.stored_flags:
    cmake_options = dsctx.stored_flags["cmake_options"]
  else:
    cmake_options = []

  cmake_options.append(f"CMAKE_GENERATOR_PLATFORM={MSVC_ARCH_MAP[msvc_arch]}")

  result = run_cmake(msvc_generator, cmake_options, dsctx.stored_flags["dry_run"])

  if result != 0:
    output.error("cmake returned {0}.".format(result))
    return CommandResult.Error

  return CommandResult.Success
