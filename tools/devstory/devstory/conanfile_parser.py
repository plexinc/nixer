import os
import re

from pathlib import Path

import redbaron

from devstory import output
from devstory.common import ds_halo

# This regex matches a valid version in our world.
VALID_VERSION_RE = r"([0-9a-z.\-]+)"
VALID_VERSION_RE_COMPILED = re.compile(VALID_VERSION_RE)

# this regex matches a package reference like:
# zlib/1.2.8
# zlib/1.0-abc123 (for git hashes)
#
PKGREF_RE = re.compile(rf"[\"\s]+([a-zA-Z\-0-9_]+)/{VALID_VERSION_RE}[\"\s]+")


class UnloadedConanFile:
  def __init__(self, name):
    self.name = name
    self.recursive_reqs = []
    self.recursive_parents = []
    self.is_loaded = False


class ParsedPlexConanFile:
  # pylint: disable=too-many-instance-attributes
  def __init__(self, path: str, data, baron):
    self.baron = baron
    self.data = data
    self.path = path
    self.requirements = {}
    self.required_by = {}

    self.plex_version = None
    self.plex_revision = None
    self.old_revision = None
    self.name = None
    self.is_loaded = True

    self.get_common_properties()

  @property
  def pkgref(self):
    return f"{self.name}/{self.plex_version}-{self.plex_revision}"

  @property
  def old_pkgref(self):
    return f"{self.name}/{self.plex_version}-{self.old_revision}"

  @property
  def revision_changed(self):
    return self.old_revision != self.plex_revision

  @property
  def recursive_reqs(self):
    for rname, req in self.requirements.items():
      if not req:
        output.warn(f"{rname} is None?")
      else:
        yield req
      for subreq in req.recursive_reqs:
        yield subreq

  @property
  def recursive_parents(self):
    for parent in self.required_by.values():
      yield parent
      for parentparent in parent.recursive_parents:
        yield parentparent

  @property
  def is_toplevel(self):
    return len(self.requirements) == 0

  @staticmethod
  def val_to_string(val):
    if not isinstance(val, (redbaron.nodes.StringNode, str)):
      print(f"Didn't get StringNode - got {val.help()}")
    string_val = str(val)

    # remove any extra spaces that indicate formatting
    string_val = string_val.strip()

    # strings from baron comes as they are in the source like "foo"
    # so here we just remove the leading and trailing "
    string_val = string_val[1:-1]
    return string_val

  def new_revision(self, revision):
    revision_assign = self.pcf.find(
      "AssignmentNode", lambda node: node.target.value == "plex_revision"
    )
    revision_assign.value.value = str(revision)
    self.plex_revision = revision

  def update_reqs(self, _):
    for req in self.requirements.values():
      if not req.is_loaded:
        continue

      for node in self.pcf.find_all("StringNode"):
        mgroup = PKGREF_RE.match(node.value)
        if not mgroup:
          continue
        if mgroup[1] == req.name:
          node.value = f'"{req.pkgref}"'

  def save_to_disk(self):
    conanfile_source = self.baron.dumps()
    if conanfile_source != self.data:
      with open(self.path, "w", newline="\n") as outfile:
        outfile.write(conanfile_source)
        return True
    return False

  def get_assignment_value(self, key):
    asn = self.pcf.find("AssignmentNode", lambda node: node.target.value == key)
    if not asn:
      raise Exception(f"Failed to find {key} in {self.path}")

    if isinstance(asn.value, redbaron.nodes.StringNode):
      return self.val_to_string(asn.value)

    if isinstance(asn.value, redbaron.nodes.IntNode):
      return int(asn.value.value)

    return None

  def get_requirements(self):
    # Getting requirements are a bit tricker. We need to first find any assignment to `plex_requires` or `plex_build_requires`,
    # then we need to find all places where we call self.plex_requires and self.plex_build_requires and grab the argument of that.
    all_req_nodes = self.pcf.find_all(
      "AssignmentNode",
      lambda node: node.target.value in ("plex_requires", "plex_build_requires"),
    )
    for node in all_req_nodes:
      if isinstance(node.value, redbaron.nodes.StringNode):
        pkgname = self.val_to_string(node.value).split("/", 1)[0]
        self.requirements[pkgname] = UnloadedConanFile(pkgname)
      elif isinstance(node.value, (redbaron.nodes.TupleNode, redbaron.nodes.ListNode)):
        for req in list(node.value):
          pkgname = self.val_to_string(req).split("/", 1)[0]
          self.requirements[pkgname] = UnloadedConanFile(pkgname)

    find_req_node = lambda name: name.value in ("plex_requires", "plex_build_requires")
    find_name_node = lambda node: node.value.find("NameNode", find_req_node)
    reqs = self.pcf.find_all("AtomtrailersNode", find_name_node)

    for req in list(reqs):
      arg = req.find("CallArgumentNode")
      pkgname = self.val_to_string(arg.value.value).split("/", 1)[0]
      self.requirements[pkgname] = UnloadedConanFile(pkgname)

  def get_common_properties(self):
    # Find the PlexConanFile subclass
    self.pcf = self.baron.find(
      "ClassNode", lambda node: node.inherit_from[0].value == "PlexConanFile"
    )
    if not self.pcf:
      raise Exception(f"Missing PlexConanFile in {self.path}")

    # What's the name?
    self.name = self.get_assignment_value("name")
    self.plex_version = self.get_assignment_value("plex_version")
    self.plex_revision = self.get_assignment_value("plex_revision")
    self.old_revision = self.plex_revision

    self.get_requirements()

  @staticmethod
  def load(path):
    from redbaron import RedBaron

    with open(path, "r", newline=None) as source:
      data = source.read()
      baron = RedBaron(data)
      return ParsedPlexConanFile(path, data, baron)
    return None


class ParsedVariantFile(ParsedPlexConanFile):
  def __init__(self, path, data, baron):
    ParsedPlexConanFile.__init__(self, path, data, baron)

  def get_common_properties(self):
    self.pcf = self.baron.find(
      "ClassNode", lambda node: node.inherit_from[0].value == "PlexConanFile"
    )
    if not self.pcf:
      raise Exception(f"Missing PlexConanFile in {self.path}")

    self.name = self.get_assignment_value("name")

  def update_reqs(self, all_packages=None):
    for req in all_packages.values():
      for node in self.pcf.find_all("StringNode"):
        mgroup = PKGREF_RE.match(node.value)
        if not mgroup:
          continue
        if mgroup[1] == req.name:
          node.value = f'"{req.pkgref}"'

  @staticmethod
  def load(path):
    from redbaron import RedBaron

    with open(path, "r", newline=None) as source:
      data = source.read()
      baron = RedBaron(data)
      return ParsedVariantFile(path, data, baron)
    return None


class ConanFileParser:
  def __init__(self, change_branch="HEAD"):
    self.all_packages = {}
    self.all_variants = {}
    self.changed_packages = {}
    self.change_branch = change_branch

  def update_changed_status(self):
    from subprocess import run, PIPE

    returnobj = run(
      ["git", "diff", "--name-status", self.change_branch],
      stdout=PIPE,
      check=True,
      stderr=PIPE,
    )
    stdoutdata = returnobj.stdout.decode("ascii")

    for line in stdoutdata.splitlines():
      try:
        change, path = line.strip().split("\t", 1)
      except ValueError:
        continue

      if Path(path).name != "conanfile.py":
        continue

      if change.strip() == "M" and "test_package" not in path:
        _, package, _ = path.split("/", 2)
        if package in self.all_packages:
          packageobj = self.all_packages[package]
          self.changed_packages[package] = packageobj
          for parent in packageobj.recursive_parents:
            if not parent.name in self.changed_packages:
              self.changed_packages[parent.name] = parent

  def load_variants_from_dir(self, rootpath):
    with ds_halo("Loading variants..."):
      for path in os.listdir(rootpath):
        cpath = os.path.join(rootpath, path, "conanfile.py")
        if os.path.exists(cpath):
          var = ParsedVariantFile.load(cpath)
          output.trace(f"Loaded variant {var.name}...")
          self.all_variants[var.name] = var

  def load_packages_from_dir(self, rootpath):
    with ds_halo("Loading conanfiles..."):
      for path in os.listdir(rootpath):
        cpath = os.path.join(rootpath, path, "conanfile.py")
        if os.path.exists(cpath):
          pcf = ParsedPlexConanFile.load(cpath)
          output.trace(f"Loaded {pcf.name}/{pcf.plex_version}-{pcf.plex_revision}...")
          self.all_packages[pcf.name] = pcf

      for package in self.all_packages.values():
        for req, req_obj in package.requirements.items():
          if isinstance(req_obj, UnloadedConanFile):
            if not req in self.all_packages:
              output.trace(f"{package.name} depends on {req} which is not loaded?")
              continue
            package.requirements[req] = self.all_packages[req]
            self.all_packages[req].required_by[package.name] = package

      self.update_changed_status()

  def update_package_versions(self):
    from itertools import chain

    saved_packages = []
    with ds_halo("Updating files..."):
      for pkg in chain(self.all_packages.values(), self.all_variants.values()):
        pkg.update_reqs(self.all_packages)
        if pkg.save_to_disk():
          saved_packages.append(pkg)
    return saved_packages

  def update_package_revisions(self, new_revisions):
    # iterate over all packages and change the package
    # revisions first.
    from itertools import chain

    saved_packages = []
    with ds_halo("Updating files..."):
      for package, revision in new_revisions.items():
        if not package in self.all_packages:
          output.warn(
            f"Wanted to update the revision for package {package} - but it wasn't loaded?"
          )
          continue

        pkg_ref = self.all_packages[package]
        pkg_ref.new_revision(revision)

      for pkg_ref in chain(self.all_packages.values(), self.all_variants.values()):
        pkg_ref.update_reqs(self.changed_packages)
        if pkg_ref.save_to_disk():
          saved_packages.append(pkg_ref)
    return saved_packages

  @staticmethod
  def print_tree(packages_in_tree):
    from asciitree import LeftAligned

    tree = {}

    def search_down(pkg):
      return {dep.name: search_down(dep) for dep in pkg.required_by.values()}

    def search_up(pkg, last=None, top=None):
      if not last:
        last = {}

      if not top:
        top = {}

      utree = {}

      if pkg.is_toplevel:
        return {pkg.name: last}

      for upkg in pkg.requirements.values():
        utree[pkg.name] = last
        if upkg.is_toplevel:
          top[upkg.name] = utree
        else:
          top.update(search_up(upkg, utree, top))

      return top

    for rpkg in packages_in_tree:
      deps = search_down(rpkg)
      tree.update(search_up(rpkg, deps))

    at = LeftAligned()
    print(at({"plex-conan": tree}))
