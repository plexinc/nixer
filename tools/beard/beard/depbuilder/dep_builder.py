#!/usr/bin/env python3
""" Main file """

import os
import optparse

from . import DependencyBuilder

from beard.common import current_context


class MainDepBuilder(object):
  """ Main class for running the dependency builder """

  def __init__(self, options):
    self.options = options
    self.root = str(current_context().home)

  @staticmethod
  def display_pkgs(operation, pkg_list):
    if pkg_list:
      return
    operation = f"  {operation} FAILED  "
    print(f"{operation:*^80}")
    for pkg in pkg_list:
      print(pkg.short_ref)
    print("*" * 80)

  def run(self):
    """ Main function """
    builder = DependencyBuilder(self.options, self.root)
    if self.options.exportandupload or self.options.only_export:
      failed_pkgs = builder.export_all()
      if failed_pkgs:
        self.display_pkgs("export_all", failed_pkgs)
        exit(1)

      if self.options.exportandupload:
        packages = builder.search_all("local", filter_namespace=False)
        failed_pkgs = builder.upload_packages(packages, False)
        if failed_pkgs:
          self.display_pkgs("upload_packages", failed_pkgs)
          exit(1)

      exit(0)

    variants = [self.options.variant]

    if self.options.variant == "auto":
      from profiles.profile_variants import profile_variants
      if not self.options.profile in profile_variants:
        print(
            "Could not find {0} in profiles/profile_variants.py, available: {1}".
            format(self.options.profile, ",".join(profile_variants)))
        exit(1)

      variants = profile_variants[self.options.profile]

    for variant in variants:
      if self.options.dev_testing:
        policy = "missing" if not self.options.force_rebuild else "package"
        failed_pkgs = builder.test_variant_package(
            variant, build_policy=policy, fail_abort=True)
        if failed_pkgs:
          self.display_pkgs(f"test_variant_package('{variant}'...)",
                            failed_pkgs)
          print("dep_builder exiting with error...")
          exit(1)
      else:
        success, failed_pkgs, test_failed_pkgs, upload_failed_pkgs = builder.build_variant(
            variant)
        if not success:
          self.display_pkgs(f"build_variant('{variant}')", failed_pkgs)
          self.display_pkgs(f"testing", test_failed_pkgs)
          self.display_pkgs(f"upload", upload_failed_pkgs)
          print("dep_builder exiting with error...")
          exit(1)

    print("dep_builder exiting with success")
    exit(0)
