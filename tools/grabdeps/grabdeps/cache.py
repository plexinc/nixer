""" This module manages the cache for dependencies """

import os
import json

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
from json.decoder import JSONDecodeError

from grabdeps.utils import unisoformat

# Find the root of where to store the deps cache
# First check PLEX_DEPS_CACHE_DIR this overrides all
# and will point to a directory we should use as the root.
#
# Then check WORKSPACE - since this is what the CI sets.
#
# Lastly just put it in $HOME/.plex_deps
#
def cache_root():
  if "PLEX_DEPS_CACHE_DIR" in os.environ:
    return Path(os.getenv("PLEX_DEPS_CACHE_DIR"))

  if "WORKSPACE" in os.environ:
    return Path(os.getenv("WORKSPACE")) / "_plex_deps"

  return Path.home() / ".plex_deps"


class Cache:
  def __init__(self, product: str, cache_dir=None):
    if not cache_dir:
      cache_dir = cache_root()
    self.root = cache_dir / product
    self.product = product
    self.root.mkdir(parents=True, exist_ok=True)

    self.tarball_cache_count = int(os.getenv("PLEX_DEPS_CACHE_TARBALL_COUNT", 10))
    self.uncompressed_cache_count = int(
      os.getenv("PLEX_DEPS_CACHE_UNCOMPRESSED_COUNT", 10)
    )
    self.axx_file = self.root / "access.json"
    if not self.axx_file.exists():
      self.access = {}
      self.save_access()
    else:
      with self.axx_file.open() as fp:
        try:
          self.access = json.load(fp)
        except JSONDecodeError as e:
          print("Failed to parse access.json - removing")
          self.access = {}
          self.save_access()

  def save_access(self):
    with self.axx_file.open("w") as fp:
      json.dump(self.access, fp, indent=2)

  def access_file(self, path: Path):
    key = str(path.relative_to(self.root))
    self.access[key] = datetime.now().isoformat()
    self.save_access()

  def is_cleanup_needed(self) -> bool:
    current_count = len(list(self.root.iterdir()))
    return current_count > self.tarball_cache_count

  def get_cleanup_items(self) -> Set[Path]:
    cleanup_items = set()
    saved_keys = set(self.access.keys())
    dir_items = set(
      str(p.relative_to(self.root))
      for p in self.root.rglob("*")
      if p.is_file() and p.name != "access.json"
    )
    # Any item that's not present in access.json will be deleted.
    # I'm sorry, I do not make the rules.
    # (actually I do, haha >:D)
    unrecorded = dir_items - saved_keys
    cleanup_items.update(unrecorded)

    # order the items by access time and delete anything after the cutoff
    ordered = list(
      reversed(sorted(self.access, key=lambda k: unisoformat(self.access[k])))
    )
    if len(ordered) > self.tarball_cache_count:
      cleanup_items.update(ordered[self.tarball_cache_count + 1 :])

    return set(Path(item) for item in cleanup_items)

  def get_cache_dir(self, sha: str) -> Path:
    return self.root / sha

  def get_tarball_path(self, sha: str, config: str, ext="zst") -> Path:
    return self.root / sha / f"{config}.tar.{ext}"
