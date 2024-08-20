import sys
import os

import click

from beard import output
from beard.common import pass_context


@click.group(invoke_without_command=True)
@click.option(
    "-v", "--verbose", help="Additional logging.", default=False, is_flag=True)
@click.option(
    "-q",
    "--quite",
    help="Only errors and warnings shown.",
    default=False,
    is_flag=True)
@click.option(
    "--version", help="Show version information", default=False, is_flag=True)
@pass_context
def cli(ctx, verbose, quite, version):
  import sys
  from beard.common import is_64bit_interpreter, get_beard_version

  if not is_64bit_interpreter():
    output.error(f"beard requires a 64-bit interpreter, but the current one "
                 f"({sys.executable}) appears to be non-64bit.")
    sys.exit(-1)

  ver_string = get_beard_version()
  output.info(f"beard v{ver_string}")
  # this flag now means "only version"
  if version:
    sys.exit(0)
  if verbose and quite:
    output.error("Please only specify one of -q and -v")
    sys.exit(1)
  ctx.verbose = verbose
  ctx.quite = quite


def default_namespace():
  user = os.getenv("CONAN_USER", "plex")
  channel = os.getenv("CONAN_CHANNEL", "stable")
  return user + "/" + channel


@cli.command(
    short_help="Builds a plex-conan tree (must be ran in envwrap to access conan)"
)
@click.option("-m", "--variant", default="auto")
@click.option("-n", "--no-export", "noexport", default=False, is_flag=True)
@click.option("-u", "--upload", default=False, is_flag=True)
@click.option("-v", "--verbose", default=False, is_flag=True)
@click.option("-j", "--jobs", "processes", default="2")
@click.option("-o", "--only-export", default=False, is_flag=True)
@click.option("-q", "--quiet-build", "quietbuild", default=False, is_flag=True)
@click.option("-p", "--profile", default=None)
@click.option("-d", "--dev-testing", default=False, is_flag=True)
@click.option("-s", "--namespace", default=default_namespace())
@click.option("-r", "--remote", default="plex")
@click.option(
    "--export-and-upload", "exportandupload", default=False, is_flag=True)
@click.option("--force-rebuild", default=False, is_flag=True)
def dep_builder(**args):
  from beard.commands.depbuilder import do_depbuilder
  do_depbuilder(args)


@cli.command(short_help="Updates package references in the current directory")
@click.option(
    "-d",
    "--dry-run",
    "dryrun",
    help="Dry Run - exit with error if not everything is updated",
    default=False,
    is_flag=True)
@click.option(
    "-b",
    "--bump",
    "bump_all",
    help="Bump all package revisions",
    default=False,
    is_flag=True)
@click.argument("extra_files", nargs=-1)
def upv(dryrun, bump_all, extra_files):
  from beard.commands.update_pkg_version import do_upv
  do_upv(dryrun, bump_all, extra_files)


@cli.command(
    short_help="Clean and filter Jenkins log saved from old UI /consoleFull")
@click.argument("html_log_file")
@click.option("-l", "--label", help="The label to filter on", default=None)
def fjl(**args):
  from beard.commands.fjl import do_fjl
  do_fjl(**args)
