# Unused variable warnings are incorrect in this file
# due to using locals() to collect the args (maybe we
# shouldn't be doing that)
# pylint: disable=W0613
import sys
from functools import wraps
from pathlib import Path

import click

from devstory import output
from devstory.common import (
  CommandResult,
  pass_context,
  using_new_toolchain,
  verify_new_toolchain,
)

# pylint: disable=protected-access
click.core._verify_python3_env = lambda: None


def require_bootstrap(func):
  @wraps(func)
  def require_bootstrap_wrapper(*args, **kwargs):
    if using_new_toolchain():
      verify_new_toolchain()
      return func(*args, **kwargs)

    if not Path("profiles").is_dir():
      output.error("Profiles directory missing, did you run " "`ds bootstrap`?")
      return None
    return func(*args, **kwargs)

  return require_bootstrap_wrapper


def require_plex_conan(func):
  @wraps(func)
  def require_plex_conan_wrapper(*args, **kwargs):
    if not Path("dep_builder.py").exists():
      output.error("Need to run any conan commands inside plex-conan dir.")
      return None
    return func(*args, **kwargs)

  return require_plex_conan_wrapper


def _run_command(msg, cmd, args=None):
  from multiprocessing.pool import ThreadPool

  from devstory.common import check_for_update

  pool = ThreadPool(processes=2)

  update_promise = pool.apply_async(check_for_update, ())

  output.info(msg, style=output.SUCCESS_STYLE)
  args = args or dict()

  try:
    result = cmd(**args)
  except:  # pylint: disable=bare-except
    result = CommandResult.Error
    output.error("There was an unhandled exception while executing the command.")
    import traceback

    traceback.print_exc()

  if result == CommandResult.Success:
    output.done("Success.")
  elif result == CommandResult.Warning:
    output.done("Finished with warnings.", output.WARN_STYLE)
  else:
    output.done("Finished with errors.", output.ERR_STYLE)

  needs_update, current_ver, latest_ver = update_promise.get()
  if needs_update:
    output.warn(
      "There is a new version of devstory "
      + f"available ({latest_ver}). Current local version is {current_ver}."
    )
    output.warn("Please run `pip3 install -U devstory`")

  status_code = 0 if result == CommandResult.Success else 1
  sys.exit(status_code)


class AliasedGroup(click.Group):
  aliases = {"👻": "bootstrap"}

  def get_command(self, ctx, cmd_name):
    rv = click.Group.get_command(self, ctx, cmd_name)
    if rv is not None:
      return rv
    matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
    if not matches:
      if cmd_name in self.aliases:
        return click.Group.get_command(self, ctx, self.aliases[cmd_name])
      return None
    if len(matches) == 1:
      return click.Group.get_command(self, ctx, matches[0])
    ctx.fail("Too many matches: %s" % ", ".join(sorted(matches)))
    return None


@click.command(cls=AliasedGroup, invoke_without_command=True)
@click.option(
  "-v", "--verbose", help="Additional logging.", default=False, is_flag=True
)
@click.option(
  "-q", "--quite", help="Only errors and warnings shown.", default=False, is_flag=True
)
@click.option("--version", help="Show version information", default=False, is_flag=True)
@pass_context
def cli(ctx, verbose, quite, version):
  from devstory.common import get_ds_version, is_64bit_interpreter

  if not is_64bit_interpreter():
    output.error(
      f"devstory requires a 64-bit interpreter, but the current one "
      f"({sys.executable}) appears to be non-64bit."
    )
    sys.exit(-1)

  ver_string = get_ds_version()
  output.info(f"devstory v{ver_string}")
  # this flag now means "only version"
  if version:
    sys.exit(0)
  if verbose and quite:
    output.error("Please only specify one of -q and -v")
    sys.exit(1)
  ctx.verbose = verbose
  ctx.quite = quite


@cli.command(short_help="Cleans up a local conan installation")
@require_bootstrap
def reset():
  """
  Cleans up a local conan installation.

  Removes all generated and installed files from the current directory.
  """
  from devstory.commands.reset import do_reset

  _run_command(
    "Cleaning up conan installation in the current directory.",
    do_reset,
  )


@cli.command(short_help="Downloads the current build profiles")
@click.option(
  "--init/--no-init",
  default=True,
  is_flag=True,
  help="Initialize conan (run conan_init)",
)
@click.option(
  "--build-dir",
  default=".",
  help="The build directory to run conan_init in. " "Default: .",
)
@click.option(
  "--remote",
  "-r",
  default=None,
  help="The conan artifactory remote to use. "
  "This overrides the value in .plex_dev or defaults to 'experimental'",
)
@click.option(
  "--ref",
  default=None,
  help="The plex-build-profiles branch, tag or SHA "
  "to download. Default: $PLEX_BUILD_PROFILES_REF or master",
)
@click.option(
  "--no-toolchain",
  default=False,
  is_flag=True,
  help="Disable installation of plextoolchain",
)
@click.option("--user-channel", "-uc", default=None, type=str)
@click.option("--user-channel-from-branch", "-ub", is_flag=True, default=False)
def bootstrap(
  init, build_dir, remote, ref, no_toolchain, user_channel, user_channel_from_branch
):
  """
  Downloads the current plex-build-profiles master.

  The repo contents are downloaded into the profiles directory.
  By default, it will also run conan_init with sane defaults.
  Use the --no-init parameter to only download.

  This command should be ran in an empty build directory inside
  the source directory.
  """
  args = locals()
  from devstory.commands.bootstrap import do_bootstrap

  _run_command("Boostrapping conan.", do_bootstrap, args=args)


@cli.command(short_help="Install dependencies for the project")
@click.option(
  "--update", "-u", default=False, is_flag=True, help="Make sure to update from remote"
)
@click.option("--build", default="never", help="Argument to conan --build")
@click.option("--build_type", default=None, help="Build type (Debug/Release)")
@click.option(
  "--profile",
  "-p",
  default=None,
  help="The profile to install. If not provided "
  "as an option, it will be asked for interactively.",
)
@click.option(
  "--variation",
  default=None,
  help="The variation to install. If not provided "
  "as an option, it will be asked for interactively.",
)
@click.option(
  "--debug-deps",
  "-d",
  default=None,
  help="Comma-separated list of dependencies to be installed with a debug configuration "
  "(even when the overall build_type is Release). "
  "Normally, the debug configurations are not built on the CI, so you will need to "
  "pass `--build missing` as well, most likely.",
)
@click.option(
  "--default",
  default=False,
  is_flag=True,
  help="Install the default (last selected) profile without prompting.",
)
@click.option(
  "--conan_options",
  "-o",
  default=None,
  multiple=True,
  help="Use -okey=value in to send options to Conan, you can pass this option"
  "several times to pass multiple values",
)
@require_bootstrap
# Click requires the argument name to match and we don't want to
# change this nor the name of the build command.
# pylint: disable=W0621
def install(
  build, build_type, profile, variation, debug_deps, update, default, conan_options
):
  """
  Installs dependencies for an interactively selected profile.

  This command is intended for cases when you want to build with a profile
  that is not native on your development machine, e.g. you are cross-compiling
  armv7 on your x86_64 Linux box or you want to control the build process
  more closely (e.g. install some debug dependencies, run cmake yourself etc.)

  If you are using an IDE, you will likely want to use one of the `dev` commands

  With multi-config generators, this may yield somewhat unexpected results:
  your build directory only holds one profile at a time. If you want to build
  multiple configurations, you will need multiple build directories.
  """
  args = locals()
  from devstory.commands.install import do_install

  _run_command("Installing dependencies.", do_install, args=args)


@cli.command(cls=AliasedGroup, short_help="Generates a tool-specific project via CMake")
@click.pass_context
@require_bootstrap
def dev(_ctx):
  """
  Generates a tool-specific projects via cmake.

  This is your one-stop-shop for building PMS in an IDE. Select one of the
  subcommands to install dependencies and generate the project/solution
  for your IDE in one step.

  When invoked without a subcommand, it will generate a ninja build.
  """
  pass


@dev.command(short_help="Generates a Visual Studio project for local development")
@click.option(
  "--variant",
  help="The PMS variant to use (can be set in config as project.variant)",
  default=None,
)
@click.option(
  "-g",
  "--generator",
  help="The CMake generator to use (can be set in config as project.cmake_generator)",
  default="Visual Studio 14 2015",
)
@click.option(
  "--cmake_options",
  "-D",
  default=None,
  multiple=True,
  help="Use -DFOO=VAL to send options to CMake, you can pass this option "
  "several times to pass multiple values",
)
@click.option(
  "--dry-run",
  "-n",
  default=False,
  is_flag=True,
  help="Don't run cmake - just print what we are going to do",
)
@click.option("--default", default=False, is_flag=True, help="Use last configuration")
@click.option(
  "--conan_options",
  "-o",
  default=None,
  multiple=True,
  help="Use -okey=value in to send options to Conan, you can pass this option"
  "several times to pass multiple values",
)
@pass_context
@require_bootstrap
def msvc(ctx, variant, generator, cmake_options, dry_run, default, conan_options):
  """
  Generates a Visual Studio project for local development.
  """
  if variant:
    ctx.stored_flags["default_variant"] = variant
  if generator:
    ctx.stored_flags["generator"] = generator
  if cmake_options:
    ctx.stored_flags["cmake_options"] = cmake_options

  ctx.stored_flags["conan_options"] = conan_options
  ctx.stored_flags["dry_run"] = dry_run
  ctx.stored_flags["default"] = default

  from devstory.commands.msvc import do_msvc

  _run_command("Setting up MSVC solution", do_msvc)


@dev.command(short_help="Generates a .xcodeproj for local development")
@click.option("--release", default=False, help="Use the release profile", is_flag=True)
@click.option(
  "--cmake_options",
  "-D",
  default=None,
  multiple=True,
  help="Use -DFOO=VAL to send options to CMake, you can pass this option "
  "several times to pass multiple values",
)
@click.option(
  "--dry-run",
  "-n",
  default=False,
  is_flag=True,
  help="Don't run cmake - just print what we are going to do",
)
@click.option(
  "--conan_options",
  "-o",
  default=None,
  multiple=True,
  help="Use -okey=value in to send options to Conan, you can pass this option"
  "several times to pass multiple values",
)
@require_bootstrap
def xcode(release, cmake_options, dry_run, conan_options):
  """
  Generates a .xcodeproj for local development.
  """
  args = locals()
  from devstory.commands.xcode import do_xcode

  _run_command("Setting up Xcode project", do_xcode, args=args)


@dev.command(short_help="Generates a CLion project for local development")
@click.option(
  "--restore", default=False, help="Restores the CLion toolchain", is_flag=True
)
@click.option(
  "--force_configs",
  "-c",
  default=False,
  help="Forces setting up build configurations. This requires "
  "manually reloading the CMake project once the directory "
  "is opened.",
  is_flag=True,
)
@require_bootstrap
def clion(restore, force_configs):
  """
  Generates a CLion project for local development.
  """
  args = locals()
  from devstory.commands.clion import do_clion

  _run_command("CLion development commands...", do_clion, args=args)


@dev.command(short_help="Generates a Ninja project for local development")
@click.option(
  "--default",
  default=False,
  is_flag=True,
  help="Install the default (last selected) profile without prompting.",
)
@click.option(
  "--cmake_options",
  "-D",
  default=None,
  multiple=True,
  help="Use -DFOO=VAL to send options to CMake, you can pass this option "
  "several times to pass multiple values",
)
@click.option(
  "--conan_options",
  "-o",
  default=None,
  multiple=True,
  help="Use -okey=value in to send options to Conan, you can pass this option"
  "several times to pass multiple values",
)
@click.option(
  "--dry-run",
  "-n",
  default=False,
  is_flag=True,
  help="Don't run cmake - just print what we are going to do",
)
@require_bootstrap
def ninja(default, cmake_options, conan_options, dry_run):
  """
  Generates a Ninja project for local development.
  """
  args = locals()
  from devstory.commands.ninja import do_ninja

  _run_command("Ninja development command...", do_ninja, args=args)


@dev.command(short_help="Generates a Visual Studio Code project for local development")
@click.option(
  "--default",
  default=False,
  is_flag=True,
  help="Install the default (last selected) profile without prompting.",
)
@click.option(
  "--cmake_options",
  "-D",
  default=None,
  multiple=True,
  help="Use -DFOO=VAL to send options to CMake, you can pass this option "
  "several times to pass multiple values",
)
@click.option(
  "--indexer",
  "-i",
  default=None,
  type=click.Choice(["ccls", "clangd", "microsoft", "none"]),
  help="Select which language server implementation you want to use.",
)
@click.option(
  "--force-settings",
  default=False,
  is_flag=True,
  help="Force write settings to .vscode/settings.json",
)
@click.option(
  "--conan_options",
  "-o",
  default=None,
  multiple=True,
  help="Use -okey=value in to send options to Conan, you can pass this option"
  "several times to pass multiple values",
)
@require_bootstrap
def vscode(default, cmake_options, indexer, force_settings, conan_options):
  """
  Generates a Visual Studio Code project for local development.
  """
  args = locals()
  from devstory.commands.vscode import do_vscode

  _run_command("VSCode development command...", do_vscode, args=args)


@cli.group(cls=AliasedGroup, short_help="To work with our conan packages")
@click.pass_context
@require_bootstrap
@require_plex_conan
def conan(ctx):
  """
  Commands to work with our conan packages.

  These commands are useful for package development. In most cases they
  save the pain of changing directories just to run a conan command in-place.
  """
  pass  # pylint: disable=unnecessary-pass


@conan.command(
  name="build", short_help="Build package or variant. Packages will be searched first"
)
@click.option(
  "-a", "--all-profiles", help="Build for all profiles", is_flag=True, default=False
)
@click.option("-b", "--build", default=None, help="--build argument to pass to conan")
@click.option(
  "-d",
  "--def-profile",
  default=False,
  is_flag=True,
  help="Use the default profile - don't prompt",
)
@click.argument("packages", nargs=-1)
@require_bootstrap
@require_plex_conan
def conan_build(all_profiles, build, packages, def_profile):
  """
  Build a package or variant. Packages will be searched first.

  For example:

      $ ds conan build zlib

  Will build the zlib package.
  """
  args = locals()
  from devstory.commands.conan import do_build

  _run_command("Building conan package/variant", do_build, args=args)


@conan.command(name="export", short_help="Export packages")
@click.option(
  "-l", "--lint", help="Enable linting - is way slower", is_flag=True, default=False
)
@click.argument("packages", nargs=-1)
@require_bootstrap
@require_plex_conan
def conan_export(lint, packages):
  """
  Exports packages.

  For example:

      $ ds conan export zlib

  Will export the zlib package.
  """
  args = locals()
  from devstory.commands.conan import do_export

  _run_command("Exporting packages", do_export, args=args)


@conan.command(name="remove", short_help="Remove package from local cache")
@click.option(
  "-e",
  "--export",
  help="Export the package after we have removed it",
  is_flag=True,
  default=False,
)
@click.argument("packages", nargs=-1)
@require_bootstrap
@require_plex_conan
def conan_remove(export, packages):
  """
  Removes packages from the local cache.

  For example:

      $ ds conan remove zlib

  Will remove the zlib package.
  """
  args = locals()
  from devstory.commands.conan import do_remove

  _run_command("Remove local conan package", do_remove, args=args)


@conan.command(
  name="versions",
  short_help="Check and adjust versions across all conanfiles - doesn't touch revisions.",
)
@require_bootstrap
@require_plex_conan
def conan_versions():
  from devstory.commands.conan import do_versions

  _run_command("Updating versions in conanfiles", do_versions)


@conan.command(name="revisions", short_help="Update revisions for all changed packages")
@click.option(
  "-l",
  "--local-versions",
  is_flag=True,
  default=False,
  help="Instead of getting the revisions from artifactory, use the local revision + 1",
)
@click.option(
  "-i",
  "--increment-with",
  nargs=1,
  default=1,
  help="Increment with more than 1 when adjusting revisions",
)
@click.option(
  "-p",
  "--print-changed-packages",
  is_flag=True,
  default=False,
  help="This prints the changed packages in a ascii-tree before doing changes.",
)
@click.option(
  "-r",
  "--remote",
  multiple=True,
  default=["experimental"],
  help="Use this artifactory remote to fetch revisions from.",
)
@click.argument("bump", default="HEAD")
@require_bootstrap
@require_plex_conan
def conan_update_revisions(
  local_versions, increment_with, print_changed_packages, remote, bump
):
  args = locals()
  from devstory.commands.conan import do_revisions

  _run_command("Update local package revisions", do_revisions, args=args)


@conan.command(name="print-tree", short_help="Print the tree for the packages suppiled")
@click.argument("packages", nargs=-1, default=None)
@require_bootstrap
@require_plex_conan
def conan_print_tree(packages):
  args = locals()
  from devstory.commands.conan import do_print_tree

  _run_command("Printing conan dependency tree", do_print_tree, args=args)


@cli.group(cls=AliasedGroup, short_help="Commands to interact with Jenkins CI")
@click.pass_context
def ci(ctx):
  pass  # pylint: disable=unnecessary-pass


@ci.command(short_help="Build a job", name="build")
@click.argument("project", nargs=1, default=None, required=False)
@click.argument("branch", nargs=1, default=None, required=False)
def ci_build(project, branch):
  """
  Trigger a build in the CI
  """
  args = locals()
  from devstory.commands.ci import do_ci_build

  _run_command("Request build from CI", do_ci_build, args=args)


@cli.command(short_help="Update dependency versions and store plex-conan SHA")
@click.option(
  "-s",
  "--source",
  default="main",
  help="Either a git ref (branch, tag or SHA) of plexinc/plex-conan or a local "
  "directory to be used as the source for package versions. If both a "
  "directory and a ref matches the name, a directory will be assumed.",
)
@click.option(
  "-c", "--commit", default=False, help="AUtomatically commit changes", is_flag=True
)
@click.argument("conanfile", type=Path)
def update(source, commit, conanfile):
  """
  Update package revisions in a conanfile to match the plex-conan repo. The --commit parameter will
  show the git diff in the current repo and offer a git commit message that contains a diff link
  to plex-conan.
  """
  args = locals()
  from devstory.commands.update import do_update

  _run_command("Update dependency versions", do_update, args)
