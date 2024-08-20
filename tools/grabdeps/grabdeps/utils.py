import os
import re
import subprocess as sp
import sys
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Union, Optional, List
from itertools import chain

from .filelock import SoftFileLock, Timeout


ZSTD_RE = re.compile(r".*v([0-9]+\.[0-9]+\.[0-9]+),.*")


@contextmanager
def no_cursor():
  if os.name == "nt":
    import ctypes
    import msvcrt

    class _CursorInfo(ctypes.Structure):
      _fields_ = [("size", ctypes.c_int), ("visible", ctypes.c_byte)]

  # pytype: disable=module-attr
  def hide_cursor():
    if os.name == "nt":
      ci = _CursorInfo()
      handle = ctypes.windll.kernel32.GetStdHandle(-11)
      ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
      ci.visible = False
      ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))
    elif os.name == "posix":
      sys.stdout.write("\033[?25l")
      sys.stdout.flush()

  def show_cursor():
    if os.name == "nt":
      ci = _CursorInfo()
      handle = ctypes.windll.kernel32.GetStdHandle(-11)
      ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
      ci.visible = True
      ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))
    elif os.name == "posix":
      sys.stdout.write("\033[?25h")
      sys.stdout.flush()

  # pytype: enable=module-attr

  try:
    hide_cursor()
    yield
  finally:
    show_cursor()


def should_print_progressbar() -> bool:
  ci_run = "BUILD_NUMBER" in os.environ
  explicitly_disabled = os.getenv("GRABDEPS_DISABLE_PROGRESSBAR", "0") == "1"
  return not (ci_run or explicitly_disabled)


def print_progressbar(done_cnt, total_cnt, total_len=30, block_char="#"):
  ratio = done_cnt / total_cnt
  blocks = block_char * int(total_len * ratio)
  spaces = " " * (total_len - int(total_len * ratio))
  percentage = int(ratio * 100)
  if should_print_progressbar():
    print(f"{percentage:4}% |{blocks}{spaces}|\r", flush=True, end="")


@contextmanager
def lock_for_dir(dirpath: Path, postfix: str = ""):
  LOCK_TIMEOUT_SECONDS = 30
  dirpath.parent.mkdir(parents=True, exist_ok=True)
  lfile = str(dirpath.parent / f"{dirpath.name}{postfix}.lock")
  lock = None
  try:
    lock = SoftFileLock(lfile, timeout=LOCK_TIMEOUT_SECONDS)
    with lock:
      yield
  except Timeout:
    # If we are here, that means we waited a long time, so the lock is likely stale.
    raise RuntimeError(
      f"Could not acquire file lock '{lfile}' after {LOCK_TIMEOUT_SECONDS}s, this lock is likely "
      "stale. Please try deleting it or check if there are other grabdeps processes running."
    )
  finally:
    if lock:
      lock.release()


def untar(tarball: Path, out_dir: Path):
  from grabdeps.plexexec import plexec

  with lock_for_dir(out_dir):
    if out_dir.is_dir():
      from shutil import rmtree

      rmtree(out_dir)

    out_dir.mkdir(exist_ok=True, parents=True)

    delete_me = False
    if tarball.suffix in (".zst", ".zstd"):
      # fmt: off
      plexec(
        [
          "zstd",
          "--long=30",  # enable long distance matching with given window log (default: 27)
          "-k",         # preserve source file(s) (default)
          "-d",         # decompression
          "-f",         # overwrite output without prompting, also (de)compress links
          "-q",         # suppress warnings; specify twice to suppress errors too
          str(tarball.resolve()),
        ],
        toolchain_path_or_ver="any",
      ).check_returncode()
      # fmt: on
      tarball = tarball.parent / tarball.name.replace(tarball.suffix, "")
      delete_me = True

    tarname = have_tar()
    if tarname:
      plexec(
        [tarname, "xf", str(tarball.resolve()), "-C", str(out_dir.resolve())],
        toolchain_path_or_ver="any",
      ).check_returncode()
    else:
      from tarfile import TarFile

      with TarFile.open(tarball.resolve(), "r:*") as tfile:
        tfile.extractall(out_dir.resolve())

    if delete_me:
      tarball.unlink()

    for fpath in out_dir.rglob("*"):
      fpath.touch()


def save_cookie(cookie: str, out_dir: Path):
  (out_dir / "current_sha.txt").write_text(cookie)


def short_circuit(cookie: str, out_dir: Path) -> bool:
  current_sha_file = out_dir / "current_sha.txt"
  if current_sha_file.exists():
    saved_sha = current_sha_file.read_text().strip()
    return saved_sha == cookie
  return False


@lru_cache(maxsize=1)
def find_plex_dev() -> Optional[Path]:
  all_cwds = []

  if "PLEX_DEV_PATH" in os.environ:
    all_cwds.append(Path(os.environ["PLEX_DEV_PATH"]).resolve())

  return find_file_in_parents(".plex_dev", all_cwds)


def find_file_in_parents(
  filename: str, parents: Optional[List[Path]] = None
) -> Optional[Path]:
  parents = parents or []
  for cwd in chain(parents, [Path.cwd(), *Path.cwd().parents]):
    fpath = cwd / filename
    if fpath.is_file():
      return fpath
  return None


DEFAULT_CONFIG = {"tools": {"conan": "1.25.2-102", "llvm_toolchain": "213"}}


@lru_cache(maxsize=1)
def parse_plex_dev():
  from configparser import ConfigParser

  config = ConfigParser()
  plex_dev_path = find_plex_dev()
  if not plex_dev_path:
    print("Can't find a .plex_dev file! Using default config.")
    config.read_dict(DEFAULT_CONFIG)
  else:
    config.read(str(plex_dev_path))
  return config


def unisoformat(timestamp: str) -> datetime:
  return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")


def sha256sum(filename: Union[str, Path]) -> str:
  from hashlib import sha256

  filehash = sha256()
  buffer = bytearray(128 * 1024)
  view = memoryview(buffer)
  with open(filename, "rb", buffering=0) as filep:
    # Disabling pytype check because of the following issue:
    # https://github.com/google/pytype/issues/1323
    for chunk in iter(
      lambda: filep.readinto(view), 0  # pytype: disable=attribute-error
    ):
      filehash.update(view[:chunk])

  return filehash.hexdigest()


def zstd_have_patch_from(zstd_version):
  from platform import system

  # Zstd seems to generate broken patches on Windows
  # https://github.com/facebook/zstd/issues/2198
  if system() == "Windows":
    return False

  mt = ZSTD_RE.match(zstd_version)
  if mt:
    from packaging import version

    # --patch-from was added in 1.4.5
    zstd_with_patch = version.parse("1.4.5")
    current_version = version.parse(mt.group(1))

    return zstd_with_patch <= current_version

  return False


@lru_cache(maxsize=1)
def have_zstd():
  from grabdeps.plexexec import plexec

  try:
    ret = plexec(
      ["zstd", "--version"], toolchain_path_or_ver="any", capture_output=True
    )
    if ret.returncode == 0:
      return True, zstd_have_patch_from(ret.stdout.decode())
  except FileNotFoundError:
    return False, False

  return False, False


def have_tar():
  from grabdeps.plexexec import plexec

  tarnames = ("tar", "gtar")

  tar_to_use = None

  for tarname in tarnames:
    try:
      ret = plexec(
        [tarname, "--version"], toolchain_path_or_ver="any", capture_output=True
      )
      if ret.returncode == 0:
        tarver = ret.stdout.decode()
        if "bsdtar" in tarver:
          continue
        tar_to_use = tarname
        break
    except FileNotFoundError:
      continue

  return tar_to_use


def platform_name():
  from platform import system

  nametable = {
    "Linux": "x86_64-linux",
    "Windows": "x86_64-windows",
    "Darwin": "x86_64-macos",
  }

  return nametable[system()]


def check_and_advise_zstd():
  install_cmds = {
    "Linux": "sudo apt install zstd",
    "Windows": "scoop install zstd",
    "Darwin": "brew install zstd",
  }
  zstd_present, _ = have_zstd()
  if not zstd_present:
    import platform

    print("The zstd executable is required to run grabdeps.")
    print(
      "An example of how you can install it (might not work in your specific env):\n"
    )
    print(f"    {install_cmds[platform.system()]}\n")
    return False
  return True


def verbose_display_python():
  if "GRABDEPS_DISPLAY_PYTHON" in os.environ:
    print(f"grabdeps using {sys.version} ({sys.executable}")
