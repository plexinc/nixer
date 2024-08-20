from pathlib import Path

from devstory import output
from devstory.common import (
  current_context,
  get_new_toolchain_cmake_options,
  get_project_dir,
  using_new_toolchain,
  wrapped_run,
  get_toolchain_from_cache,
  DsConfig,
)


def run_cmake_new_toolchain(generator: str, options: dict, dry_run: bool):
  cmake_options, toolchain_file = get_new_toolchain_cmake_options()

  if options:
    cmake_options += [f"-D{opt}" for opt in options]

  toolchain_in_cache = get_toolchain_from_cache()

  if toolchain_in_cache and toolchain_file != toolchain_in_cache:
    output.error(
      f"Toolchain file set in cache: {toolchain_in_cache.name} is different from what"
    )
    output.error(
      "you configured now. You need to remove CMakeCache.txt or use a different"
    )
    output.error("dir in order to continue.")
    return 1

  output.info("Running CMake...")
  cmd = ["cmake", f"-G{generator}"]
  cmd += cmake_options
  cmd += [str(get_project_dir())]
  result = wrapped_run(cmd, dry_run=dry_run)
  return result


def run_cmake(generator: str, options=None, dry_run=None):
  if using_new_toolchain():
    return run_cmake_new_toolchain(generator, options, dry_run)
  old_cache = Path("CMakeCache.txt")
  if old_cache.exists():
    output.info("Previous CMake cache found, removing.")
    old_cache.unlink()

  cmake_options = ["-DSKIP_COMPILER_CHECK=ON"]

  ctx = current_context()
  profile = getattr(ctx, "profile", None)
  if profile:
    try:
      cmake_options.append(f"-DPROFILE_ID={profile.env['PLEX_PACKAGE_TARGET']}")
    except KeyError:
      pass

  variation = getattr(ctx, "variation", None)
  plex_dev = DsConfig.load_plex_dev()
  if variation:
    variant_key = plex_dev.load_setting(
      "project", "variant_key", "PLEX_MEDIA_SERVER_VARIATION"
    )
    try:
      cmake_options.append(f"-D{variant_key}={variation}")
    except KeyError:
      pass

  if options:
    cmake_options += [f"-D{opt}" for opt in options]

  output.info("Running CMake...")
  cmd = ["cmake", f"-G{generator}"]
  initial_cache = Path("initial-cache.cmake").resolve()
  if initial_cache.exists():
    cmd += [f"-C{initial_cache}"]
  cmd += cmake_options
  cmd += [str(get_project_dir())]
  result = wrapped_run(cmd, dry_run=dry_run)
  return result
