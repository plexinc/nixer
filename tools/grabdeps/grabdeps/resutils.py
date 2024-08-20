import pkg_resources

from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, List, Optional


IGNORE = "*.pyc", "__init__.py"


def is_ignored(fname: str) -> bool:
  return any(fnmatch(fname, pat) for pat in IGNORE)


def iter_resdir_files(res_pkg: str, glob_pattern: str) -> Iterable[Path]:
  resdir = get_resdir(res_pkg)
  for item in resdir.glob(glob_pattern):
    if item.is_file() and not is_ignored(item.name):
      yield item


def get_resdir(res_pkg: str) -> Path:
  init_py = Path(pkg_resources.resource_filename(res_pkg, "__init__.py"))
  return init_py.parent
