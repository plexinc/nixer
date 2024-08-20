from pathlib import Path
from shutil import copyfileobj
from subprocess import run

from grabdeps.cache import Cache
from grabdeps.downloader import Downloader
from grabdeps.utils import platform_name


# check if there is a patch for the toolchains we have
# available and the target version.
def check_patch_filename(version: str, cache: Cache, downloader: Downloader):

  toolchains = [
    tlc for tlc in cache.get_cache_dir(version).parent.iterdir() if tlc.is_dir()
  ]
  toolchains = sorted(toolchains, reverse=True)

  for tlc in toolchains:
    patchname = f"{platform_name()}-patch-from-{tlc.name}.zst"
    path = f"/llvm-toolchain/{version}/{patchname}"
    if downloader.head(path):
      return patchname, tlc

  return None, None


def patch_file(patch_file: Path, patch_from: Path):
  from grabdeps.plexexec import plexec

  # find the old toolchain file that we need.
  from_file = [
    patch_from / f"{platform_name()}.tar.{ext}"
    for ext in ("zst", "xz")
    if (patch_from / f"{platform_name()}.tar.{ext}").is_file()
  ][0]

  unpacked_from = patch_file.parent / from_file.name.replace(
    platform_name(), f"{platform_name()}-tmp"
  ).replace(from_file.suffix, "")

  print(f"Unpacking {from_file}...")
  if from_file.suffix == ".xz":
    import lzma

    with lzma.open(patch_from / from_file, "rb") as compfp:
      with open(unpacked_from, "wb") as uncompf:
        copyfileobj(compfp, uncompf)
  else:
    # unpack it
    ret = plexec(
      [
        "zstd",
        "--memory=2048MB",
        "-d",
        "-k",
        "-f",
        f"{patch_from / from_file}",
        "-o",
        str(unpacked_from),
      ],
      toolchain_path_or_ver="any",
    )
    ret.check_returncode()

  # Patch the old tar file with the patch file we have
  # downloaded. This gives us the new tarfile.
  final_file = patch_file.parent / f"{platform_name()}.tar"
  cmd = [
    "zstd",
    "--memory=2048MB",
    "-d",
    "-k",
    "-f",
    f"--patch-from={unpacked_from}",
    str(patch_file),
    "-o",
    str(final_file),
  ]

  ret = plexec(cmd, toolchain_path_or_ver="any")
  # we don't need the old file anymore
  unpacked_from.unlink()
  ret.check_returncode()

  # Do a quick compression of the patched file
  # we favor speed over compression here.
  cmd = ["zstd", "--long=30", "--rm", "--fast", "-f", str(final_file)]

  plexec(cmd, toolchain_path_or_ver="any").check_returncode()

  return final_file
