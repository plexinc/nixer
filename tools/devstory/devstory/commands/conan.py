import sys
import os
import shutil

from pathlib import Path

from devstory.common import (
  CommandResult,
  select_profile,
  run_command,
  conan_bin_name,
  get_project_dir,
  get_all_viable_profiles,
  default_profile,
)
from devstory import output


def do_remove(export, packages):
  conan_user_home = Path(os.environ.get("CONAN_USER_HOME", Path.home() / ".conan_plex"))
  all_pkg = [Path(conan_user_home / ".conan" / "data" / pkg) for pkg in packages]
  for pkg in all_pkg:
    if pkg.exists():
      output.info("Removing " + str(pkg))
      shutil.rmtree(str(pkg))

  if export:
    do_export(False, [p.name for p in all_pkg])


def do_export(lint, packages):
  all_pkg = []
  if packages:
    all_pkg = [Path(get_project_dir() / "packages" / pkg) for pkg in packages]
  else:
    all_pkg = [x for x in Path(get_project_dir() / "packages").iterdir()]

  for pkg in all_pkg:
    if Path(pkg / "conanfile.py").exists():
      output.info("Exporting " + pkg.name)
      ret = run_command(
        [sys.executable, conan_bin_name(), "export", pkg, "plex/stable"],
        env={"CONAN_RECIPE_LINTER": "True" if lint else "False"},
      )
      if ret != 0:
        output.warn("Failed to export package: " + str(pkg))
        return CommandResult.Error
  return CommandResult.Success


def _get_profiles(all_profiles, def_profile):
  if all_profiles:
    selected_profiles = get_all_viable_profiles()
  else:
    if def_profile:
      selected_profiles = [default_profile()]
      output.info("Using default profile: " + selected_profiles[0].name)
    else:
      selected_profiles = [select_profile()]

  return selected_profiles


def do_build(all_profiles, build, packages, def_profile):
  paths_to_build = []

  for pkg in packages:
    pkg_path = Path("packages" / Path(pkg) / "conanfile.py")
    var_path = Path("variants" / Path(pkg) / "conanfile.py")

    if pkg_path.exists():
      paths_to_build.append(pkg_path)
    elif var_path.exists():
      paths_to_build.append(var_path)
    else:
      output.error("Failed to find package: " + pkg)
      return CommandResult.Error

  selected_profiles = _get_profiles(all_profiles, def_profile)

  for selected_profile in selected_profiles:
    for pkg_path in paths_to_build:
      pkg_name = str(pkg_path.parents[0]).replace(str(pkg_path.parents[1]) + "/", "")
      is_package = str(pkg_path.parents[1]) == "packages"

      output.info(
        "Building {}: {}, profile: {}".format(
          "package" if is_package else "variant", pkg_name, selected_profile.name
        )
      )

      if is_package:
        args = [
          sys.executable,
          conan_bin_name(),
          "create",
          "-pr",
          selected_profile.path,
          pkg_path,
          "plex/stable",
        ]
        if build:
          args += ["--build", build]

        ret = run_command(args)

      else:
        build_args = "--build=outdated" if not build else "build=" + build
        ret = run_command(
          [
            sys.executable,
            conan_bin_name(),
            "install",
            "-pr",
            selected_profile.path,
            build_args,
            pkg_path,
          ]
        )

      if ret != 0:
        output.error(
          "Failed to build: {} profile: {}".format(pkg_name, selected_profile.name)
        )
        return CommandResult.Error

  return CommandResult.Success


def do_print_tree(packages):
  from devstory.conanfile_parser import ConanFileParser

  cfp = ConanFileParser()
  cfp.load_packages_from_dir("packages")
  loaded_packages = [
    cfp.all_packages[name] for name in packages if name in cfp.all_packages
  ]
  cfp.print_tree(loaded_packages)
  return CommandResult.Success


def _print_changed_packages(updated):
  if updated:
    output.info("Changed packages:")
    for u in updated:
      output.info(f"  - {u.path}")
  else:
    output.info("No packages changed...")


def do_versions():
  from devstory.conanfile_parser import ConanFileParser

  cfp = ConanFileParser()
  cfp.load_packages_from_dir("packages")
  cfp.load_variants_from_dir("variants")
  _print_changed_packages(cfp.update_package_versions())

  return CommandResult.Success


def do_revisions(local_versions, increment_with, print_changed_packages, remote, bump):
  from devstory.conanfile_parser import ConanFileParser
  from devstory.conan_remote import ConanRemote

  change_branch = "HEAD" if bump == "all" else bump
  cfp = ConanFileParser(change_branch=change_branch)
  cfp.load_packages_from_dir("packages")
  cfp.load_variants_from_dir("variants")

  if print_changed_packages:
    cfp.print_tree(cfp.changed_packages.values())
    return CommandResult.Success

  packages = []
  if bump == "all":
    packages = cfp.all_packages.values()
  else:
    packages = cfp.changed_packages.values()

  if not local_versions:
    fixed_remotes = []
    for rem in remote:
      if rem.startswith("groundzero"):
        fixed_remotes.append(rem)
      else:
        fixed_remotes.append(f"conan-{rem}")

    cremote = ConanRemote(fixed_remotes)
    new_revisions = cremote.next_revisions_for_packages(packages)
  else:
    new_revisions = {
      pkg.name: pkg.old_revision + increment_with for pkg in packages if pkg.is_loaded
    }

  updated = cfp.update_package_revisions(new_revisions)
  _print_changed_packages(updated)
  return CommandResult.Success
