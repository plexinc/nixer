from pathlib import Path
from typing import List

from devstory import output
from devstory.common import (
  CommandResult,
  conan,
  current_context,
  get_info_file,
  get_project_dir,
  is_cmake_deps,
  select_profile,
  select_variation,
  using_new_toolchain,
)


# Constructs the arg list passed to conan to select
# build types for individual packages.
def _get_debug_deps_args(debug_deps: str) -> List[str]:
  if not debug_deps:
    return []
  debug_deps_items = (item.strip() for item in debug_deps.split(","))
  args = []
  for dep in debug_deps_items:
    args += [f"-s{dep}:build_type=Debug"]
  return args


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def do_install(
  build, build_type, profile, variation, debug_deps, update, default, conan_options
):
  if using_new_toolchain():
    return CommandResult.Success

  if get_project_dir() == Path.cwd():
    output.error(
      "Please do not run install from the root directory. " "Create a build dir first."
    )
    return CommandResult.Error
  cmake_deps = is_cmake_deps()

  project_dir = str(get_project_dir())

  info_file = get_info_file()
  output.info("Clearing any existing install configuration from .ds_info")
  info_file.delete_setting("configuration", "install")
  info_file.delete_setting("configuration", "profile")

  selected_profile = select_profile(profile, select_default=default)

  if not variation:
    selected_variation = select_variation(selected_profile, select_default=default)
  else:
    selected_variation = variation

  if not cmake_deps:
    output.info("Inspecting conanfile...")
    inspect_data = conan.inspect(project_dir)
    output.info(f"Installing for project {inspect_data['name']}")

    info_file = get_info_file()
    remote = info_file.load_setting("devstory", "remote")
    if remote is None:
      output.error(
        "Could not read the devstory.remote setting from .ds_info. "
        "Please bootstrap again."
      )
      return CommandResult.Error

    output.info(
      "Installing dependencies for {0}/{1}. "
      "This may take a minute or two".format(selected_profile.name, selected_variation)
    )

    debug_deps_args = _get_debug_deps_args(debug_deps)

    other_install_args = []
    if build_type:
      other_install_args = ["-sbuild_type=" + build_type]

    if update:
      other_install_args.append("--update")

    ioptions = inspect_data["options"]
    options = []
    if conan_options:
      for optionstr in conan_options:
        key = optionstr.split("=")[0]

        if key not in ioptions:
          output.error(f"Couldn't find option '{key}' in conanfile via conan inpsect!")
          output.error(f"Available options are: {', '.join(ioptions.keys())}")
          return CommandResult.Error

        options.append(f"-o{optionstr}")

    if "variation" in ioptions:
      options.append(f"-ovariation={selected_variation}")

    if "devel" in ioptions:
      options.append("-odevel=True")

    ret = conan.install(
      [
        project_dir,
        "-pr",
        selected_profile.path,
        "--build=" + build,
        "--remote=" + remote,
        *debug_deps_args,
      ]
      + other_install_args
      + options,
      save="install",
    )

    if ret != 0:
      output.error("conan returned " + str(ret))
      return CommandResult.Error

  ctx = current_context()
  info_file.save_setting("configuration", "profile", str(selected_profile.path))
  info_file.save_setting("configuration", "variation", selected_variation)
  if cmake_deps:
    ctx.profile = selected_profile
    ctx.variation = selected_variation
  else:
    output.info("Dependencies installed.")

  return CommandResult.Success
