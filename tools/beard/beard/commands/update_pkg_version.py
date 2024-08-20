#!/usr/bin/env python3

import os
import re
import shutil
import tempfile
import optparse
import sys

from collections import defaultdict

from beard.depbuilder.crunner import CRunner, OutputBuffer
from beard.common import Bunch, current_context

OPTIONS = None
ROOTDIR = current_context().home
PKGDIR = os.path.join(ROOTDIR, "packages")
VARIANTDIR = os.path.join(ROOTDIR, "variants")

# This regex matches a valid version in our world.
VALID_VERSION_RE = r"([0-9a-z.\-]+)"
VALID_VERSION_RE_COMPILED = re.compile(VALID_VERSION_RE)

# this regex matches a package reference like:
# zlib/1.2.8
# zlib/1.0-abc123 (for git hashes)
#
PKGREF_RE = re.compile(r"[\"\s]+([a-zA-Z\-0-9_]+)/{validversion}[\"\s]+".format(
    validversion=VALID_VERSION_RE))

ALL_PACKAGES = {}
PACKAGE_REV_MAPPING = defaultdict(list)
RUN = CRunner()


class Package(object):
  # pylint: disable=too-many-instance-attributes
  rootdir = PKGDIR

  def __init__(self, name):
    self.name = name

    # stores version and revision from the file as is on disk
    self.version = None
    self.revision = -1

    # stores the version and revision from the file in git HEAD
    # can be same as above if the file hasn't changed
    self.head_version = None
    self.head_revision = -1

    # this is set to True if *we* did any change to file doesn't care
    # about changes compared to git head.
    self.changed = False

    self.requires = []
    self.conanfile = os.path.join(self.rootdir, self.name, "conanfile.py")
    test_conanfile = os.path.join(self.rootdir, self.name, "test_package",
                                  "conanfile.py")
    if os.path.isfile(test_conanfile):
      self.test_conanfile = test_conanfile
    else:
      self.test_conanfile = None

    # figure out if the file has changed from git HEAD
    self.changed_from_head = self.has_changed_from_head()

    # populate version/revision and head_version/head_revision
    self.get_version()
    self.get_git_head_versions()

    # update revision in the file on disk if needed.
    self._correct_changed_file()

  def __str__(self):
    return self.name

  def export_package(self):
    # function to export the package to conan used when we change the
    # conanfile from this script.
    def get_conan_bin():
      import platform
      if platform.system() == "Windows":
        return "conan-bin.py"
      else:
        return "conan-bin"

    RUN("\"{exe}\" {conan} export {dir} {user}/{channel}".format(
        exe=sys.executable,
        conan=os.path.join(ROOTDIR, get_conan_bin()),
        user=os.getenv("CONAN_USERNAME", "plex"),
        channel=os.getenv("CONAN_CHANNEL", "stable"),
        dir=os.path.dirname(self.conanfile)),
        output=True)

  @property
  def new_revision(self):
    # since the file has changed we need to bump revision
    # from HEAD - but only if the version hasn't changed.
    # if the version has changed we set revision to 0 to
    # reset it.
    #
    newrev = self.head_revision + 1
    if not self.version == self.head_version:
      newrev = 0

    return newrev

  def _correct_changed_file(self):
    # this function checks if the file has changed from HEAD
    # and then makes sure that we have bumped the revision.
    if not self.changed_from_head:
      return

    newrev = self.new_revision

    if not self.revision is newrev:
      print("{}: file changed from HEAD, correcting revision: {} -> {}".format(
          self.name, self.full_version, self._full_version(
              self.version, newrev)))
      self.revision = newrev
      self.changed = True
      self.changed_from_head = True

  @property
  def relative_conanfile(self):
    # TODO: this is ugly.
    return self.conanfile.replace(os.getcwd() + os.path.sep, "").replace(
        os.path.sep, "/")

  def has_changed_from_head(self):
    # git diff --exit-code behaves like straight diff to exit
    # with a 1 if the file has changed or 0 if it's not changed.
    cmd = "git diff --exit-code --name-only HEAD {}".format(
        self.relative_conanfile)
    return RUN(cmd, output=None) is 1

  def get_git_head_versions(self):
    # get revision and version from git HEAD, done
    # by calling git show HEAD:file
    if not self.changed_from_head:
      self.head_revision = self.revision
      self.head_version = self.version
      return

    git_buffer = OutputBuffer()
    cmd = "git show HEAD:{}".format(self.relative_conanfile)
    if RUN(cmd, output=git_buffer) is not 0:
      print("Failed to run git show HEAD:{}\n{}".format(self.conanfile,
                                                        git_buffer))
      sys.exit(1)

    self.head_version, self.head_revision = self.parse_version(git_buffer.lines)

  @property
  def packageref(self):
    return "{}/{}".format(self.name, self.full_version)

  @property
  def full_head_version(self):
    return self._full_version(self.head_version, self.head_revision)

  @property
  def full_version(self):
    return self._full_version(self.version, self.revision)

  @staticmethod
  def _full_version(version, revision):
    return "{0}{1}".format(version, ""
                           if revision == -1 else "-{0}".format(revision))

  def parse_version(self, lines):
    version, cversion, revision = None, None, -1
    for line in lines:
      if line.startswith("  plex_version"):
        version = line.split("\"")[1]
      elif line.startswith("  plex_revision"):
        revision = int(line.split("=")[1].strip())
      elif line.startswith("  version"):
        cversion = line.split("\"")[1]

    if version:
      if not VALID_VERSION_RE_COMPILED.match(
          self._full_version(version, revision)):
        raise Exception("Failed to parse version {}".format(
            self._full_version(version, revision)))
    elif cversion:
      if not VALID_VERSION_RE_COMPILED.match(cversion):
        raise Exception("Failed to parse version {}".format(cversion))

      if not "-" in cversion:
        version = cversion
        revision = 0
      else:
        version, revision = cversion.split("-")
        revision = int(revision)

    return version, revision

  def get_version(self):
    if not os.path.exists(self.conanfile):
      raise Exception("Could not find file: {0}".format(self.conanfile))

    with open(self.conanfile, "r", newline="") as cfp:
      self.version, self.revision = self.parse_version(cfp)

  def write_revision(self):
    openfile, tmpfile = tempfile.mkstemp("plex")
    os.close(openfile)
    with open(
        self.conanfile, "r", newline="") as cfp, open(
            tmpfile, "w+", newline="") as target:
      for line in cfp:
        if line.startswith("  plex_revision ="):
          target.write("  plex_revision = {0}\n".format(self.revision))
        else:
          target.write(line)

    shutil.move(tmpfile, self.conanfile)

  def process_requires(self):
    changed_in_this_context = False

    files = [self.conanfile]
    if self.test_conanfile:
      files.append(self.test_conanfile)

    for conanfile in files:
      openfile, tmpfile = tempfile.mkstemp("plex")
      os.close(openfile)
      with open(
          conanfile, "r", newline="") as cfp, open(
              tmpfile, "w+", newline="") as target:
        for line in cfp:
          writeline = line
          matches = PKGREF_RE.findall(line)
          for match in matches:
            writeline, changed_in_this_context = self.process_requirement(
                match, writeline, changed_in_this_context,
                conanfile == self.test_conanfile)

          if not OPTIONS.dryrun:
            target.write(writeline)
      if not OPTIONS.dryrun:
        shutil.move(tmpfile, conanfile)

    return changed_in_this_context

  def process_requirement(self, match, line, _changed, is_test=False):
    newline = line
    changed = _changed
    if match[0] in ALL_PACKAGES:
      pack = ALL_PACKAGES[match[0]]
      if not self.name in PACKAGE_REV_MAPPING[match[0]]:
        PACKAGE_REV_MAPPING[match[0]].append(self.name)

      currentref = "{0}/{1}".format(match[0], match[1])
      if pack.packageref != currentref:
        test_postfix = " (test_package)" if is_test else ""
        print(f"{self.name}: {currentref} -> {pack.packageref}{test_postfix}")
        newline = line.replace(currentref, pack.packageref)
        if not self.changed:
          self.changed = True
          self.revision = self.new_revision
          changed = True

    return newline, changed


class Variant(Package):
  rootdir = VARIANTDIR

  def get_version(self):
    pass

  def get_git_head_versions(self):
    pass

  def has_changed_from_head(self):
    return False


class VariantFile(Variant):
  def __init__(self, name):
    Variant.__init__(self, os.path.basename(name))
    self.conanfile = name


def process_packages(packages):
  # Step 1: go through all packages once and check the references of their requirements
  # if something has changed the process_requires() will return True to indicate that
  # this package now have a new revision.
  #
  updated_packages = []
  for pkg in packages:
    if OPTIONS.bump_all:
      ALL_PACKAGES[pkg].revision = ALL_PACKAGES[pkg].new_revision
      updated_packages.append(pkg)
    elif ALL_PACKAGES[pkg].process_requires():
      updated_packages.append(pkg)

  # Now loop over all packages that has changed. Since chaging one package will
  # most likely change it recursively.
  # Continue this loop until a run no longer returns packages that has been changed.
  #
  while True:
    processing = []

    for pkg in updated_packages:
      for req in PACKAGE_REV_MAPPING[pkg]:
        if ALL_PACKAGES[req].process_requires():
          processing.append(req)

    if len(processing) == 0:
      break

    updated_packages = processing

  # End by acutally commiting the revision change.
  # This is just done once to avoid bumping the revision
  # multiple times in one run.
  #
  anything_changed = 0
  for pkg in list(ALL_PACKAGES.values()):
    if pkg.changed or OPTIONS.bump_all:
      anything_changed += 1
      if not OPTIONS.dryrun:
        pkg.write_revision()

        # export the package if we have changed
        # it so it's ready to use directly.
        pkg.export_package()

  return anything_changed


def process_variants(extra_files=None):
  if extra_files is None:
    extra_files = []

  variants_changed = []
  for var in os.listdir(VARIANTDIR):
    if os.path.exists(os.path.join(VARIANTDIR, var, "conanfile.py")):
      if Variant(var).process_requires():
        variants_changed.append(var)

  for extra in extra_files:
    if not os.path.exists(extra):
      print("Could not find extra file {}".format(extra))
      sys.exit(1)
    else:
      print("Processing: {}".format(extra))
      VariantFile(extra).process_requires()

  return len(variants_changed)


def load_packages():
  for pkg in os.listdir(PKGDIR):
    # skip . dirs and plexconantool + conanwrap
    if pkg in ("jsonenv",) or pkg[0] == '.':
      continue

    if os.path.exists(os.path.join(PKGDIR, pkg, "conanfile.py")):
      ALL_PACKAGES[pkg] = Package(pkg)


def do_upv(dryrun, bump_all, extra_files):
  global OPTIONS  # pylint: disable=global-statement
  OPTIONS = Bunch(locals())

  # first we load information about all packages. But not information about their
  # own requirements. We want to do this at a later stage.
  #
  load_packages()

  # Now we go through all the packages and their requirements to see if the version
  # number is up to date.
  #
  packages_changed = process_packages(list(ALL_PACKAGES.keys()))

  # Lastly we update the variants.
  var_changed = process_variants(extra_files)

  if OPTIONS.dryrun:
    if packages_changed or var_changed:
      print(
          "ERROR: not all versions are updated correctly, please run update_pkg_version.py before commiting!"
      )
      sys.exit(1)

  sys.exit(0)


if __name__ == '__main__':
  main()
