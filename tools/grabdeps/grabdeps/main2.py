import sys
from argparse import ArgumentParser, REMAINDER
from pathlib import Path

import poyo

from grabdeps.cache import Cache
from grabdeps.version import get_grabdeps_version, check_yaml_version
from grabdeps.downloader import Downloader
from grabdeps.utils import (
  check_and_advise_zstd,
  find_file_in_parents,
  parse_plex_dev,
  save_cookie,
  short_circuit,
  untar,
  verbose_display_python,
)
from grabdeps.yml_utils import (
  get_tarball_name,
  get_deps_buildinfo_path,
  write_superbuildinfo,
  write_superbuildinfo_json,
  write_super_sharedlib_list,
  parse_config_spec,
  get_configs_for_dep,
  get_sha,
  remap_configs,
  filter_configs,
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

  plex_dev = parse_plex_dev()

  parser = ArgumentParser()
  parser.add_argument(
    "-o",
    "--output-dir",
    type=Path,
    default=plex_dev.get("defaults", "output_dir", fallback="dependencies"),
    help="Where to extract the dependencies. Can be an absolute or relative path.",
  )
  parser.add_argument(
    "-u",
    "--url",
    default=plex_dev.get(
      "defaults", "deps_url", fallback="https://artifacts.plex.tv/conan-bundles"
    ),
    help="Where to download dependencies from",
  )
  parser.add_argument(
    "-d",
    "--deps-file",
    type=lambda fname: poyo.parse_string(Path(fname).read_text()),
    default=str(
      find_file_in_parents(plex_dev.get("defaults", "deps_file", fallback="deps.yml"))
    ),
    help="Yaml file listing the deps to install",
  )
  parser.add_argument(
    "-v",
    "--variant",
    default=plex_dev.get("defaults", "variant", fallback=None),
    help="An optional variant filter to allow conditional deps per variant",
  )
  parser.add_argument("configs", nargs=REMAINDER)
  args = parser.parse_args()

  output_dir = Path(args.output_dir)
  print(f"Using output directory: {str(output_dir)}")

  if not check_yaml_version(args.deps_file):
    print(
      f"Yaml config version in file (v{args.deps_file['!version']}) is not understood by this version of grabdeps."
    )
    print("Please upgrade!")
    sys.exit(-2)

  buildinfos = []
  parsed_configs = parse_config_spec(args.configs)
  for product, entry in args.deps_file.items():
    if product == "!version":
      continue
    if "for-variant" in entry:
      if args.variant != entry["for-variant"]:
        continue
    sha = get_sha(entry)
    configs = entry.get(
      "configs", get_configs_for_dep(dep_name=product, cfg_specs=parsed_configs)
    )
    if not configs:
      print(
        f"WARNING: Skipping '{product}' because no configs were specified on the command line or in deps.yml"
      )
      continue

    # Filter the list first
    configs = filter_configs(entry, configs, args.variant)

    # Then remap if we need
    configs = remap_configs(entry, configs)

    for config in configs:
      # variables that are available for the format string
      naming_context = {"config": config, "variant": args.variant}
      tarball_name = get_tarball_name(entry, naming_context)
      tarball_path = f"/{product}/{sha}/{tarball_name}.tar.zst"
      print(f"Fetching: {args.url}{tarball_path}")
      cfg_output_dir = output_dir / product / tarball_name
      subdir = entry.get("directory")
      if subdir:
        cfg_output_dir = cfg_output_dir / subdir

      deps_id = f"{config}@{sha}"

      buildinfos.append(get_deps_buildinfo_path(product, entry, naming_context))

      if short_circuit(deps_id, cfg_output_dir):
        print(f"  - already extracted, remove current_sha.txt to force overwriting.")
        continue

      cache = Cache(product)
      downloader = Downloader(args.url, cache)
      downloader.download(tarball_path)

      untar(cache.get_tarball_path(sha, tarball_name), cfg_output_dir)
      save_cookie(deps_id, cfg_output_dir)
    print()

  write_superbuildinfo(output_dir / "plex-buildinfo.cmake", buildinfos)
  write_superbuildinfo_json(output_dir / "buildinfo.json", buildinfos, args)
  write_super_sharedlib_list(output_dir / f"shared-libs.cmake")


if __name__ == "__main__":
  main()
