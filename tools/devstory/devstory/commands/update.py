import re
import subprocess as sp

from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Dict, List
from contextlib import contextmanager

from devstory import output
from devstory.common import run_command, work_dir, CommandResult


PLEX_CONAN_REPO = "plexinc/plex-conan"

# matches a line like:
#   name = "foo"
NAME_RGX = re.compile(r'\s*name\s*=\s*f?"(.+)"')

# matches a line like:
#   plex_version = "1.3-6"
#   version = "1.3-6"
VER_RGX = re.compile(r'\s*(?:plex_)?version\s*=\s*f?"(.+)"')

# matches a line like:
#   plex_revision = 6
REV_RGX = re.compile(r"\s*plex_revision\s*=\s*(\d+)")

# matches a package reference like:
#   zlib/1.2.8
#   zlib/1.2.8-3
#   zlib/1.0-abc123-4
PKGREF_RE = re.compile(r"([a-zA-Z\-0-9_]+)/([0-9a-z.\-]+)")


class PackageRef:
  def __init__(self, name: str, version: str):
    self.name = name
    self.version = version

  def __str__(self):
    return f"{self.name}/{self.version}"


def load_refs(repo: Path) -> Dict[str, PackageRef]:
  # pylint: disable=too-many-branches
  refs = {}
  pkgs_dir = repo / "packages"
  output.info(f"Loading recipes from {str(pkgs_dir)}")
  for pkgdir in pkgs_dir.iterdir():
    if not pkgdir.is_dir():
      continue
    conanfile = pkgdir / "conanfile.py"
    if not conanfile.exists():
      output.warn(f"No conanfile in package directory: {str(pkgdir.resolve())}")
      continue

    # this is a slightly ugly, but pretty fast way to load these values
    # from the conanfiles
    name, version, revision = None, None, None
    with conanfile.open() as contents:
      for line in contents:
        if name is None:
          result = NAME_RGX.search(line)
          if result:
            name = result.group(1)
            if name and version and revision:
              break
            continue
        if version is None:
          result = VER_RGX.search(line)
          if result:
            version = result.group(1)
            if name and version and revision:
              break
            continue
        if revision is None:
          result = REV_RGX.search(line)
          if result:
            revision = result.group(1)
            if name and version and revision:
              break
            continue

    refs[name] = PackageRef(name, f"{version}-{revision}")
  return refs


def update_conanfile(conanfile: Path, refs: Dict[str, PackageRef]):
  output.info(f"Updating {str(conanfile.resolve())}")
  lines = open(conanfile).readlines()
  with conanfile.open("w") as fp:
    for line in lines:
      result = PKGREF_RE.search(line)
      if result:
        name = result.group(1)
        if name not in refs:
          fp.write(line)
          continue
        ref = str(refs[name])
        if result.group(0) != ref:
          start, end = result.span()
          print(f"{result.group(0):34} -> {ref}")
          line = line[:start] + ref + line[end:]
      fp.write(line)


@contextmanager
def temp_git_checkout(ref: str) -> Path:
  with TemporaryDirectory(suffix="_ds_update_clone") as tmpdir:
    output.info(f"Temp checkout in {tmpdir}")
    with work_dir(tmpdir):
      run_command(["git", "clone", f"git@github.com:{PLEX_CONAN_REPO}"])
      with work_dir("plex-conan"):
        run_command(["git", "checkout", ref])
        git = sp.run(["git", "rev-parse", "HEAD"], stdout=sp.PIPE, check=True)
        git_ref = git.stdout.decode().strip()
        yield Path().cwd().resolve(), git_ref


def make_commit(commit_msg: str, files: List[str]):
  from devstory.common import is_truthy

  git = sp.run(["git", "--no-pager", "diff", "--exit-code", *files])
  if git.returncode == 0:
    output.warn("There were no changes.")
    return
  should_commit = is_truthy(input("Create git commit? [Y/n] ") or "Y")
  if not should_commit:
    output.info("Skipping commit creation")
    return
  with TemporaryDirectory(suffix="_ds_update_commit") as tmp:
    commit_text_path = None
    with work_dir(tmp):
      commit_text_file = Path("commit.txt")
      commit_text_file.write_text(f"{commit_msg}\n")
      commit_text_path = str(commit_text_file.resolve())
    sp.run(["git", "commit", "-t", commit_text_path, *files])


def do_update(source: str, commit: bool, conanfile: Path):
  conanfile = conanfile.resolve()
  refs = {}
  git_ref = None
  files = [conanfile]

  if Path(source).is_dir():
    refs = load_refs(Path(source))
    with work_dir(source):
      git = sp.run(["git", "rev-parse", "HEAD"], stdout=sp.PIPE, check=True)
      git_ref = git.stdout.decode().strip()
  else:
    with temp_git_checkout(source) as git_info:
      repo, git_ref = git_info
      refs = load_refs(repo)

  update_conanfile(conanfile, refs)

  old_plex_conan_sha = None
  repo_plex_dev = conanfile.parent / ".plex_dev"
  if repo_plex_dev.exists():
    output.info("Saving info to project .plex_dev")
    from devstory.common import get_sha256, DsConfig

    plex_dev = DsConfig(repo_plex_dev)
    conanfile_hash = get_sha256(conanfile)
    old_plex_conan_sha = plex_dev.load_setting("info", "plex_conan_sha")
    plex_dev.save_setting("info", "plex_conan_sha", git_ref)
    plex_dev.save_setting("info", "conanfile_sha256", conanfile_hash)
    files.append(repo_plex_dev)

  output.info("Displaying commit message recommendation")
  diff_link = ""
  if old_plex_conan_sha is not None:
    diff_link = f"\n\nhttps://github.com/plexinc/plex-conan/compare/{old_plex_conan_sha[:10]}...{git_ref[:10]}"

  commit_msg = (
    f"conan: update dependencies to <short reason, e.g. get openssl fix>{diff_link}"
  )
  print(commit_msg)

  if commit:
    make_commit(commit_msg, files)

  return CommandResult.Success
