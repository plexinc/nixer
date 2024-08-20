import os
import sys
import subprocess
import tempfile

from .common import run_command, get_conan_path, get_info_file


class Conan:
  def __call__(self, args, **kwargs):
    return self._conan(*args, **kwargs)

  @staticmethod
  def _silent_conan(*args, **kwargs):
    conan_path = str(get_conan_path())
    if not os.path.exists(conan_path):
      from devstory import output

      output.warn(
        "conan-bin does not exist. " "You probably need to run `ds bootstrap` first."
      )
      return None
    return subprocess.run(
      [sys.executable, str(conan_path), *args],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      **kwargs,
    )

  @staticmethod
  def _conan(*args, **kwargs):
    conan_path = str(get_conan_path())
    if not os.path.exists(conan_path):
      from devstory import output

      output.warn(
        "conan-bin does not exist. " "You probably need to run `ds bootstrap` first."
      )
      return None
    return run_command([sys.executable, str(conan_path), *args], **kwargs)

  def install(self, args, save=False, **kwargs):
    if save:
      ds_info = get_info_file()
      args = [str(arg) for arg in args]
      ds_info.add_to_list("configuration", save, args)
    return self(["install", *args], **kwargs)

  def inspect(self, path):
    from json import load

    with tempfile.TemporaryDirectory() as tmpdir:
      ret = self._silent_conan("inspect", f"-j{tmpdir}/inspect.json", path)
      ret.check_returncode()
      with open(f"{tmpdir}/inspect.json", "r") as jsonfp:
        inspect_data = load(jsonfp)
        return inspect_data

  @staticmethod
  def export_pkg(args, user_home=None):
    migrated = False
    env = (
      {"CONAN_USER_HOME": user_home, "PLEX_CONAN_USER_HOME": "1"} if user_home else None
    )
    original_env = os.environ.copy()
    if env:
      original_env.update(env)
    proc = Conan._silent_conan("export-pkg", *args, env=original_env)
    if "ERROR: Invalid setting" in proc.stdout.decode():
      migrated = True
    return proc.returncode, migrated
