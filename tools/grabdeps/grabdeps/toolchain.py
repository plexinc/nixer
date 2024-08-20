#!/usr/bin/env python3

import argparse
import os
import pathlib
import sys
from platform import system

from grabdeps.cache import Cache
from grabdeps.downloader import Downloader
from grabdeps.filelock import SoftFileLock
from grabdeps.patches import check_patch_filename, patch_file
from grabdeps.utils import (
  have_zstd,
  lock_for_dir,
  parse_plex_dev,
  platform_name,
  save_cookie,
  short_circuit,
  untar,
)


def move_stuff_around(output_dir: pathlib.Path):
  toolchain_dir = output_dir / "plex-llvm-toolchain"
  if system() == "Windows":
    toolchain_dir = output_dir / "plex-llvm-toolchain-windows-x86_64"
  for subdir in toolchain_dir.glob("*"):
    subdir.rename(toolchain_dir.parent / subdir.name)
  toolchain_dir.rmdir()


def get_toolchain_path(version=None):
  if not version or version == "any":
    plex_dev = parse_plex_dev()
    actual_version = plex_dev.get("tools", "llvm_toolchain")
    if actual_version:
      version = actual_version

  if not version:
    return None

  output_dir = os.getenv("PLEX_TOOLCHAIN_CACHE", None)
  if not output_dir:
    output_dir = pathlib.Path.home() / ".plex_toolchain"
  else:
    output_dir = pathlib.Path(output_dir)

  if not output_dir.is_dir():
    output_dir.mkdir(parents=True)

  if version == "any":
    available_toolchains = sorted(
      [p for p in output_dir.iterdir() if (p / "deployed.txt").is_file()], reverse=True
    )
    if available_toolchains:
      version = available_toolchains[0].name

  return output_dir / version


def download_toolchain(url, version=None, output_dir=None):
  if not version:
    plex_dev = parse_plex_dev()
    version = plex_dev.get("tools", "llvm_toolchain", fallback=None)

  if not version:
    return None

  if not output_dir:
    output_dir = get_toolchain_path(version)

  if not output_dir:
    # get_toolchain_path can return None, so we check it again
    # but this time we can't do anything.
    raise RuntimeError(
      "Can't determine toolchain path. Is the version set in .plex_dev?"
    )

  output_dir.mkdir(parents=True, exist_ok=True)

  # Hold the lock
  with lock_for_dir(output_dir, postfix="download"):
    if short_circuit(version, output_dir):
      return output_dir

    cache = Cache("llvm_toolchain")
    downloader = Downloader(url, cache)

    ext = ""
    patch_from = None
    zstd, zstd_patch_from = have_zstd()
    if zstd:
      toolchain_filename = None
      # Check if we can patch instead of download the whole file
      if zstd_patch_from:
        toolchain_filename, patch_from = check_patch_filename(
          version, cache, downloader
        )
        if toolchain_filename:
          print(f"Using patch: {toolchain_filename}")

      if not toolchain_filename:
        toolchain_filename = f"{platform_name()}.tar.zst"

      ext = "zst"
    else:
      toolchain_filename = f"{platform_name()}.tar.xz"
      ext = "xz"

    path = f"/llvm-toolchain/{version}/{toolchain_filename}"
    print(f"Fetching {url}/{path}")
    downloader.download(path)

    if patch_from:
      patch_file(cache.get_cache_dir(version) / toolchain_filename, patch_from)
      untar(cache.get_tarball_path(version, platform_name(), "zst"), output_dir)
    else:
      print(f"Unpacking into {output_dir} ...")
      untar(cache.get_tarball_path(version, platform_name(), ext), output_dir)
    if version.isnumeric():
      # Old versions of the toolchain were identified by a numeric build number.
      # Newer versions contain the LLVM version and the hash of clang-builder. Incidentally,
      # this new format came with a change in the toolchain layout, so we no longer need to
      # move the files around after extracting.
      move_stuff_around(output_dir)
    save_cookie(version, output_dir)

  return output_dir


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "-o",
    "--output-dir",
    default=None,
    help="Where to extract the dependencies. Can be an absolute or relative path.",
  )
  parser.add_argument(
    "-u",
    "--url",
    default="https://artifacts.plex.tv/clang-plex",
    help="Where to download dependencies from",
  )
  parser.add_argument(
    "-v", "--version", default=None, help="Toolchain version, overriden from .plex_dev"
  )
  args = parser.parse_args()

  download_toolchain(args.url, args.version, args.output_dir)
