import os
import platform
import sys
from argparse import ArgumentParser, REMAINDER
from pathlib import Path
from subprocess import PIPE, run

from grabdeps.toolchain import download_toolchain, get_toolchain_path
from grabdeps.utils import verbose_display_python


def get_exec_env(toolchain_path_or_ver=None):
  exec_env = os.environ.copy()
  toolchain_path = toolchain_path_or_ver or None
  if toolchain_path is None:
    toolchain_path = get_toolchain_path()
  elif toolchain_path == "any":
    toolchain_path = get_toolchain_path(version="any")

  # For Windows we add /lib to the path as well so that the .dll files can be found
  if platform.system() == "Windows":
    exec_env["PATH"] = os.pathsep.join(
      (
        str(toolchain_path / "bin"),
        str(toolchain_path / "targets" / "x86_64-w64-mingw32" / "bin"),
        exec_env["PATH"],
      )
    )
  else:
    exec_env["PATH"] = os.pathsep.join((str(toolchain_path / "bin"), exec_env["PATH"]))
  exec_env["PLEX_TOOLCHAIN_PATH"] = str(toolchain_path)
  return exec_env


def plexec(command, toolchain_path_or_ver=None, capture_output=False):
  exec_env = get_exec_env(toolchain_path_or_ver)
  shell = False

  if not command:
    print("This is plexec, your friendly neighborhood command wrapper.")
    print("I will make sure to run commands in the current toolchain.")
    sys.exit(0)

  cmd = Path(command[0])
  if not cmd.is_absolute():
    # check if the command is in the toolchain path first
    suffix = ".exe" if platform.system() == "Windows" else ""
    possible_path = Path(exec_env["PLEX_TOOLCHAIN_PATH"]) / "bin" / f"{cmd}{suffix}"
    if possible_path.is_file():
      command[0] = str(possible_path)

  if capture_output:
    ret = run(command, env=exec_env, stdout=PIPE, stderr=PIPE, shell=shell)
  else:
    ret = run(command, env=exec_env, shell=shell)
  return ret


def print_env(varname, toolchain_path_or_ver):
  env = get_exec_env(toolchain_path_or_ver)
  value = env.get(varname, None)
  print(value)


def main():
  verbose_display_python()
  parser = ArgumentParser(add_help=False)
  parser.add_argument("-e", "--print-env")
  parser.add_argument("cmd", nargs=REMAINDER)
  args = parser.parse_args()

  toolchain_path = download_toolchain("https://artifacts.plex.tv/clang-plex")

  if args.print_env:
    print_env(args.print_env, toolchain_path)
  else:
    sys.exit(plexec(args.cmd, toolchain_path).returncode)


if __name__ == "__main__":
  main()
