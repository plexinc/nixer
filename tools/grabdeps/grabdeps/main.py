import sys
from argparse import ArgumentParser
from pathlib import Path

from grabdeps.cache import Cache
from grabdeps.downloader import Downloader
from grabdeps.utils import (
  check_and_advise_zstd,
  save_cookie,
  short_circuit,
  untar,
  verbose_display_python,
)


def main():
  verbose_display_python()
  if "--version" in sys.argv:
    from grabdeps.version import get_grabdeps_version

    print(get_grabdeps_version())
    sys.exit(0)

  if not check_and_advise_zstd():
    print("Aborting due to missing zstd.")
    sys.exit(1)

  parser = ArgumentParser()
  parser.add_argument(
    "-o",
    "--output-dir",
    default="dependencies",
    help="Where to extract the dependencies. Can be an absolute or relative path.",
  )
  parser.add_argument(
    "-u",
    "--url",
    default="https://artifacts.plex.tv/conan-bundles",
    help="Where to download dependencies from",
  )
  parser.add_argument("product")
  parser.add_argument("sha", help="The complete plex-conan SHA (shortened won't work)")
  parser.add_argument("config")
  args = parser.parse_args()

  output_dir = Path(args.output_dir)

  deps_id = f"{args.config}@{args.sha}"

  if short_circuit(deps_id, output_dir):
    print(
      "Dependencies already present. Remove current_sha.txt from the dependencies dir"
    )
    print("to force replacing them.")
    sys.exit()

  cache = Cache(args.product)
  downloader = Downloader(args.url, cache)
  downloader.download(f"/{args.product}/{args.sha}/{args.config}.tar.zst")

  untar(cache.get_tarball_path(args.sha, args.config), output_dir)
  save_cookie(deps_id, output_dir)


if __name__ == "__main__":
  main()
