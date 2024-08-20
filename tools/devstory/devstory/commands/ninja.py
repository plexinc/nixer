import click

from devstory import output
from devstory.common import CommandResult, run_cmake


def do_ninja(default, cmake_options, conan_options, dry_run):
  from devstory.commands.install import do_install

  ctx = click.get_current_context()
  inst_result = ctx.invoke(
    do_install,
    build="never",
    build_type=None,
    profile=None,
    variation=None,
    debug_deps=None,
    update=False,
    conan_options=conan_options,
    default=default,
  )

  if inst_result != CommandResult.Success:
    return inst_result

  result = run_cmake("Ninja", cmake_options, dry_run)

  if result != 0:
    output.error("cmake returned {0}.".format(result))
    return CommandResult.Error

  return CommandResult.Success
