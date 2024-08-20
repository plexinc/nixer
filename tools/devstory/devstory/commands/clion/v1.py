from devstory.common import CommandResult


def do_clion(*args, **kwargs):  # pylint: disable=unused-argument
  print(
    """
    This project is using the pre-musl toolchain which is no longer supported in devstory for CLion.

    The latest version that did support it is 1.522. Either downgrade to that, or use the new
    toolchain (have llvm_toolchain = xxx in .plex_dev)
    """
  )

  return CommandResult.Success
