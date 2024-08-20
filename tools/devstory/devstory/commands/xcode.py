import click
from devstory import output
from devstory.commands.install import do_install
from devstory.common import CommandResult, get_native_profile, run_cmake


def do_xcode(release, cmake_options, dry_run, conan_options):
  profile = get_native_profile(debug=not release)

  ctx = click.get_current_context()
  results = ctx.invoke(
    do_install,
    build="never",
    build_type="RelWithDebInfo" if release else "Debug",
    profile=profile.name,
    variation="standard",
    debug_deps=None,
    update=False,
    default=False,
    conan_options=conan_options,
  )

  if results != CommandResult.Success:
    return results

  cmake_result = run_cmake("Xcode", cmake_options, dry_run)
  if cmake_result != 0:
    output.error("cmake returned {0}.".format(cmake_result))
    return CommandResult.Error
  return CommandResult.Success
