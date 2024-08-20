import shutil
import os
import glob

from devstory import output
from devstory.common import CommandResult


def do_reset():
  patterns = [
    "conan-*.py",
    "conan-bin",
    "conan-bin.py",
    "envwrap.py",
    "conanenv*.json",
    ".conan_*",
    ".conan-lib",
    "profiles",
    "conanbuildinfo*",
  ]
  removed = 0
  for pattern in patterns:
    for match in glob.glob(pattern):
      output.trace("Removing {0}".format(match))
      try:
        if os.path.isdir(match):
          shutil.rmtree(match, ignore_errors=True)
        else:
          os.remove(match)
        if os.path.islink(match):
          os.unlink(match)
      except IOError:
        output.error("Could not remove " + match)
        return CommandResult.Error
      removed += 1
  if removed == 0:
    output.warn("Nothing was removed. Are you in the right directory?")
    return CommandResult.Warning
  return CommandResult.Success
