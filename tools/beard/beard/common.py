from pathlib import Path

import click


class BeardContext(object):
  def __init__(self):
    import pathlib
    self.verbose = False
    self.quite = False
    self.home = pathlib.Path().cwd()


pass_context = click.make_pass_decorator(BeardContext, ensure=True)

_default_context = BeardContext()


def current_context() -> object:
  try:
    return click.get_current_context().obj
  except RuntimeError:
    return _default_context


def get_project_dir(indicators=None):
  """ Tries to determine the project directory in relation to the working dir """
  def find_up(path):
    last_dir = Path(".").resolve()
    current_dir = last_dir
    while True:
      full_path = current_dir / path
      if full_path.exists():
        return full_path
      # pylint is wrong about this:
      #
      #     E1101:Instance of 'PurePath' has no 'resolve' member
      #
      # https://github.com/PyCQA/pylint/issues/224
      # pylint: disable=E1101
      last_dir = current_dir.resolve()
      current_dir = Path(current_dir / "..").resolve()
      if last_dir == current_dir:
        return None
  project_root_indicators = indicators or (".git", "conanfile.py", "conanfile.txt")
  for indicator in project_root_indicators:
    path = find_up(indicator)
    if path:
      return path.parents[0]
  raise RuntimeError("Could not determine project root dir. Maybe you "
                     "need to add an item to the `project_root_indicators`")


# This class provides a simple way to turn dictionaries into object attributes
class Bunch(object):
  def __init__(self, adict):
    self.__dict__.update(adict)


def get_beard_version() -> str:
  from pkg_resources import get_distribution
  return get_distribution("beard").version


def is_64bit_interpreter() -> bool:
  import sys
  # This is the most reliable way to check the interpreter bitness
  # because universal binaries on macOS may run in 32 bit mode.
  # https://docs.python.org/2/library/platform.html#platform.architecture
  # https://stackoverflow.com/a/1842699/140367
  return sys.maxsize > 2**32
