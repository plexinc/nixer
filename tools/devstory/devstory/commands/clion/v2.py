from devstory.common import CommandResult, get_toolchain_path


def get_toolchain_targets():
  toolchain_dir = get_toolchain_path() / "toolchains"
  return sorted(path.stem for path in toolchain_dir.iterdir())


def do_clion(*args, **kwargs):  # pylint: disable=unused-argument
  print(
    """
    You don't need devstory to build this project in CLion anymore.

    You might wish to run `ds boostrap` to make sure you have an up-to-date toolchain.

    Otherwise, simply open the PMS folder and a default configuration will be
    selected for you.

    Cross compiling: Go to 'File -> Settings -> Build, Execution, Deployment -> CMake' and
    add -DTOOLCHAIN_TARGET= with one of the following values:\n"""
  )

  for target in get_toolchain_targets():
    print(f"{' '*8}- {target}")

  print(
    """
    (Depending on your current platform, you might not see any cross-compiled targets
    in the above list. That means cross-compiling is not supported on the current platform.)"""
  )

  print(
    """
    To select the variation (standard/nano), you can pass -DPLEX_MEDIA_SERVER_VARIATION similarly.
    The default is Standard everywhere, except on iOS and tvOS.
    """
  )

  return CommandResult.Success
