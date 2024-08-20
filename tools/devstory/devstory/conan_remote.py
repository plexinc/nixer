from devstory.artifactory import Artifactory
from devstory.common import ds_halo

CONAN_REMOTES = (
  "conan-experimental",
  "conan-stable",
  "conan-test",
  "groundzero-adam",
  "groundzero-tamas",
  "groundzero-tobias",
  "groundzero-rcombs",
  "groundzero-tim",
)


class ConanPackageVersion:
  def __init__(self, version):
    self.raw_version = version
    self.version, self.revision = self.raw_version.rsplit("-", 1)

  def __eq__(self, other):
    return self.raw_version == other.raw_version

  def __ne__(self, other):
    return not self.raw_version == other.raw_version

  def __lt__(self, other):
    if self.version == other.version:
      return int(self.revision) < int(other.revision)

    return self.version < other.version

  def __le__(self, other):
    if self.version == other.version:
      return int(self.revision) <= int(other.revision)

    return self.version <= other.version

  def __gt__(self, other):
    if self.version == other.version:
      return int(self.revision) > int(other.revision)

    return self.version > other.version

  def __repr__(self):
    return self.raw_version


class ConanRemote:
  def __init__(self, remotes=CONAN_REMOTES):
    self.art = Artifactory.default()
    self.remotes = remotes

  def list_all_versions(self, package):
    from concurrent.futures import as_completed, ThreadPoolExecutor

    futures = []
    with ThreadPoolExecutor(max_workers=len(self.remotes)) as pool:
      for remote in self.remotes:
        # pylint: disable=protected-access
        # I mean we shouldn't really access proctected members here and it should
        # be refactored in the future - for now we just cheat.
        url = self.art._api(f"storage/{remote}/plex/{package}")
        ftr = pool.submit(self.art._get, url)
        futures.append(ftr)

    all_versions = []
    for ftr in as_completed(futures):
      response = ftr.result()
      if response.status_code == 200:
        jdata = response.json()
        for entry in jdata["children"]:
          if entry["folder"]:
            all_versions.append(entry["uri"][1:])

    all_versions = list(set(all_versions))
    all_versions = sorted(all_versions, key=ConanPackageVersion)

    return all_versions

  def next_revision(self, package, version):
    # remove revision
    version_no_rev = version.rsplit("-", 1)[0]
    matching_versions = [
      ver for ver in self.list_all_versions(package) if ver.startswith(version_no_rev)
    ]

    # we know the list is sorted - so just grab the last one
    if matching_versions:
      highest_version = matching_versions[-1]
      return int(highest_version.rsplit("-", 1)[-1]) + 1
    return 0

  def next_revisions_for_packages(self, packages):
    from concurrent.futures import as_completed, ThreadPoolExecutor

    data = {}
    ftr_to_package = {}
    with ds_halo("Fetching revisions from artifactory..."):
      with ThreadPoolExecutor(max_workers=8) as pool:
        for pkg in packages:
          pkgname, pkgversion = pkg.pkgref.split("/")
          ftr = pool.submit(self.next_revision, pkgname, pkgversion)
          ftr_to_package[ftr] = pkgname

      for ftr in as_completed(ftr_to_package):
        pkgname = ftr_to_package[ftr]
        data[pkgname] = ftr.result()

    return data


if __name__ == "__main__":
  cr = ConanRemote(["conan-experimental"])
  versions = cr.next_revision("zlib", "1.2.8")
  print(versions)
