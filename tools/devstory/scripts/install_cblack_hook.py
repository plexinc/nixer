#! /usr/bin/env python

import os.path
import platform
import subprocess as sp


def get_git_dir():
  try:
    stdout = sp.check_output(["git", "rev-parse", "--absolute-git-dir"])
    return stdout.decode("utf-8").strip()
  except sp.CalledProcessError:
    return None


def install_githook():
  sig = "# !!! plex cblack hook !!!"
  template = f"""#!/bin/bash
{sig}
# ^^^ don't delete or change the above line ^^^
MY_DIR=$(dirname "$0")
cblack --check $MY_DIR
"""
  hooks_dir = os.path.join(get_git_dir(), "hooks")
  pre_commit_file = os.path.join(hooks_dir, "pre-commit")
  if os.path.exists(pre_commit_file):
    try:
      lines = open(pre_commit_file).readlines()
      if len(lines) > 4:
        print("Non-empty pre-commit hook detected, not overwriting")
        print("This is what I would have written into the file:")
        print(template)
        return
      sig_in_file = lines[1].strip()
      if sig_in_file == sig:
        return
    except IndexError:
      pass
  with open(pre_commit_file, "w") as hookfile:
    hookfile.write(template)
  if platform.system() != "Windows":
    os.chmod(pre_commit_file, 0o775)


if __name__ == "__main__":
  install_githook()
