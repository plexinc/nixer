""" Our main dependency builder """
import os, platform, collections
from concurrent.futures import Future, ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import signal
import sys
import re

from beard.depbuilder import ConanRunner, InfoParser
from beard.depbuilder.buildinfoparser import PackageInfo

NEED_BUILD_MAP = {}
MAX_WORKERS = int(os.environ.get("PLEX_CONAN_MAX_JOBS", 6))


def get_pct_version():
  version_rgx = r'version = "(?P<version>[\d\-]+)"'
  pct_conanfile = "packages/plexconantool/conanfile.py"
  if not os.path.isfile(pct_conanfile):
    return "0-0"  # a bogus value is fine, it's used for filtering
  with open(pct_conanfile) as pct:
    for line in pct:
      match = re.search(version_rgx, line)
      if match:
        return match.group("version")
  raise RuntimeError("Could not read PCT version")


class DependencyBuilder(object):
  """ Main class for doing all dependency building """

  def __init__(self, options, root):
    self.options = options
    self.rootdir = root
    self.conan = ConanRunner(self.rootdir, options)

  def export_all(self):
    """ export all packages under the packages folder """
    if self.options.noexport:
      return True

    pkg_to_future = {}
    failed = []
    exported = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
      for directory in os.listdir(os.path.join(self.rootdir, "packages")):
        conanfile = os.path.join(self.rootdir, "packages", directory,
                                 "conanfile.py")
        if os.path.exists(conanfile):
          ftr = pool.submit(self.conan.export_package, directory)
          pkg_to_future[ftr] = directory

      for future in as_completed(pkg_to_future):
        pkgname = pkg_to_future[future]
        export_res = False
        try:
          export_res = future.result()
        except Exception as exc:
          print("export package {} failed with exception: {}".format(
              pkgname, exc))
          failed.append(pkgname)
        else:
          if export_res:
            exported.append(pkgname)
          else:
            failed.append(pkgname)

    if failed:
      self._send_slack(
          "Export finished",
          "Exported {0} packages".format(len(exported)), [],
          "Failed to export",
          failed,
          failed=(len(failed) > 0))

    return failed

  def upload_packages(self, packages, binaries=True, force=False):
    """ upload all packages """
    uploaded = []
    failed = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
      pkgs_to_future = {}
      for package in packages:
        future = None
        if package.built:
          for pkg_id in package.package_id:
            future = pool.submit(
                self.conan.upload_package,
                package.reference,
                force=force,
                binaries=binaries,
                package_id=pkg_id)
        elif not binaries:
          future = pool.submit(
              self.conan.upload_package,
              package.reference,
              force=force,
              binaries=False)
        pkgs_to_future[future] = package

      for future in as_completed(pkgs_to_future):
        pkgname = pkgs_to_future[future]
        upload_res = False
        try:
          upload_res = future.result()
        except Exception as exc:
          print("upload package {} failed with exception: {}".format(
              pkgname, exc))
          failed.append(pkgname)
        else:
          if upload_res:
            uploaded.append(pkgname)
          else:
            failed.append(pkgname)

    return failed

  def build_variant(self, variant):
    """ issue a full build of a variant """
    #self._send_slack("Starting {0}build of {1}...".format("*forced* " if self.options.force_rebuild else "", variant))
    vardir = os.path.join(self.rootdir, "variants", variant)
    build = "outdated"

    if self.options.force_rebuild:
      build = "*"

    success = True
    packageinfo = self.conan.install(vardir, build, update=True)

    upload_failed, build_failed = [], []

    if len(packageinfo.get("failed")) > 0:
      build_failed = [pkg for pkg in packageinfo.get("failed")]
      success = False
      self._send_slack(
          "Failed to build {}. Continuing to testing.".format(", ".join(
              (b.short_ref for b in build_failed))),
          failed=True)

    if len(packageinfo.get("built")) > 0:
      built_packages = [pkg.short_ref for pkg in packageinfo.get("built")]
      self._send_slack("Built the following packages: " +
                       ", ".join(built_packages))

    self._send_slack("Installed {} packages".format(
        len(packageinfo.get("installed"))))

    info = collections.defaultdict(dict)
    pkglist = []
    if os.path.exists("conaninfo.txt"):
      info, pkglist = InfoParser.get_options("conaninfo.txt")
    else:
      print("NO conaninfo.txt FOUND! Might be a problem!")

    # Filter out all packages not in the conaninfo.txt - they will be private requires
    # and we don't know the options for private requires and can't test them correctly.
    pkgs_to_test = [
        p for p in packageinfo.get("built", []) if p.name in pkglist
    ]

    packages_to_upload, failed_test_packages = self.test_packages(
        info, pkgs_to_test)

    # now add the packages we can't test - just upload them - always.
    packages_to_upload += [
        p for p in packageinfo.get("built", []) if not p.name in pkglist
    ]

    if failed_test_packages:
      success = False

    if self.options.upload:
      upload_failed = self.upload_packages(packages_to_upload, True)
      if success:
        success = not (upload_failed or build_failed)

    return success, build_failed, failed_test_packages, upload_failed

  def test_packages(self, info, packages):
    options = InfoParser.get_options_str(info)
    failed = []
    success = []

    for pkg in packages:
      if not self.conan.test_package(pkg.reference, self.options.dev_testing,
                                     "never", options):
        failed.append(pkg)
      else:
        success.append(pkg)

    self.clean_packages(success)
    return success, failed

  def test_variant_package(self,
                           variant,
                           info=collections.defaultdict(dict),
                           build_policy="never",
                           fail_abort=False):
    """ run conan test_package on all the packages in a test_variant """
    build_order = self.conan.build_order(variant)

    success_packages = []
    failed_packages = []

    for packages in build_order:
      for packageref in packages:
        options = InfoParser.get_options_str(info)

        if not self.conan.test_package(packageref, self.options.dev_testing,
                                       build_policy, options):
          failed_packages.append(packageref)
          if fail_abort:
            return success_packages, False
        else:
          success_packages.append(packageref)

    self.clean_packages(success_packages)

    if len(failed_packages) > 0:
      self._send_slack(
          "Packages tested",
          failed_title="Failed tests",
          failed_packages=failed_packages,
          failed=len(failed_packages) > 0)

    return failed_packages

  def clean_packages(self, packages):
    """ clean all packages """
    pkg_to_future = {}
    failed = []
    removed = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
      for pkg in packages:
        ftr = pool.submit(self.conan.remove_package, pkg.reference)
        pkg_to_future[ftr] = pkg

      for future in as_completed(pkg_to_future):
        pkg = pkg_to_future[future]
        try:
          future.result()
        except Exception as exc:
          print("remove package {} failed with exception: {}".format(
              pkgname, exc))
          failed.append(pkg)
        else:
          removed.append(pkg)

    if failed:
      self._send_slack(
          "Remove finished",
          "Removed {0} packages".format(len(removed)), [],
          "Failed to remove",
          failed,
          failed=(len(failed) > 0))
      return False

    return True

  def search_all(self, remote, filter_namespace=True):
    """ proxy for conan.search_all """
    pkgs_unfilt = (
        PackageInfo(x) for x in self.conan.search_all(remote, filter_namespace))
    pct_version = get_pct_version()
    pkgs = []
    for pkg in pkgs_unfilt:
      if (pkg.name == "plexconantool" and pkg.version != pct_version) or \
          pkg.name == "plextesttool":
        continue
      pkgs.append(pkg)
    return pkgs

  # pylint: disable=too-many-arguments
  def _send_slack(self,
                  message,
                  success_title=None,
                  success_packages=None,
                  failed_title=None,
                  failed_packages=None,
                  failed=False):
    """ send a slack message - if no slack token is available just print it to stdout """

    if not success_packages:
      success_packages = []

    if not failed_packages:
      failed_packages = []

    print(message)
