from pathlib import Path

from devstory import output
from devstory.common import (
  CommandResult,
  get_native_profile,
  wrapped_run,
  get_project_dir,
  conan,
  current_context,
  get_info_file,
  DsConfig,
  run_cmake,
)


def _install_profile(config):
  profile = get_native_profile(debug=(config == "Debug"))
  info_file = get_info_file()
  remote = info_file.load_setting("devstory", "remote")
  output.info(f"Installing profile '{profile}' for {config} configs")
  conan_flags = [
    str(get_project_dir()),
    "-pr",
    str(profile.path),
    "-r",
    remote,
    "-g",
    "cmake_multi",
    "-s",
    f"build_type={config}",
    "-o",
    "devel=True",
  ]
  ctx = current_context()

  # load the default variant from context (i.e. passed as flag) or config
  # and default to the first item of all_variants, if present
  plex_dev = DsConfig.load_plex_dev()
  all_variants = plex_dev.load_list_setting("project", "variants", [None])
  variant = plex_dev.load_project_setting_ctx(ctx, "default_variant", all_variants[0])
  if variant:
    conan_flags += ["-o", f"variation={variant}"]

  ret = conan.install(conan_flags)
  if ret != 0:
    output.error("conan returned {0}".format(ret))
    return False
  return True


def do_msvc():
  ctx = current_context()

  info_file = get_info_file()
  output.info("Clearing any existing install configuration from .ds_info")
  info_file.delete_setting("configuration", "install")

  if not _install_profile("Debug"):
    return CommandResult.Error
  buildinfo = ctx.home / "conanbuildinfo.txt"
  bi_debug = Path("conanbuildinfo_debug.txt")
  if bi_debug.exists():
    bi_debug.unlink()
  buildinfo.rename(bi_debug)

  if not _install_profile("Release"):
    return CommandResult.Error
  buildinfo = ctx.home / "conanbuildinfo.txt"
  bi_release = Path("conanbuildinfo_release.txt")
  if bi_release.exists():
    bi_release.unlink()
  buildinfo.rename(bi_release)

  # Work around for https://github.com/conan-io/conan/issues/6219
  conanbuildinfo_multi = open("conanbuildinfo_multi.cmake").read()
  conanbuildinfo_multi = conanbuildinfo_multi.replace("_RELWITHDEBINFO", "_RELEASE")
  with open("conanbuildinfo_multi.cmake", "w") as fp:
    fp.write(conanbuildinfo_multi)

  plex_dev = DsConfig.load_plex_dev()
  generator = plex_dev.load_project_setting_ctx(
    ctx, "cmake_generator", "Visual Studio 14 2015"
  )
  cmake_result = run_cmake(
    generator,
    options=plex_dev.load_project_setting_ctx(ctx, "cmake_options"),
    dry_run=plex_dev.load_project_setting_ctx(ctx, "dry_run"),
  )
  if cmake_result != 0:
    output.error("cmake returned {0}.".format(cmake_result))
    return CommandResult.Error

  post_script = plex_dev.load_setting("commands.msvc", "after")
  if post_script is not None:
    output.info("Running post-msvc script")
    variables = {"project_dir": get_project_dir(), "build_dir": ctx.home}
    post_script = post_script.format(**variables)
    import shlex

    parts = shlex.split(post_script, posix=False)
    if Path(parts[0]).suffix == ".py":
      import sys

      parts.insert(0, sys.executable)
    wrapped_run(parts)

  return CommandResult.Success
