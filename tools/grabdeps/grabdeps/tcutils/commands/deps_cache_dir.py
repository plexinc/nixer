from typing import TextIO, Optional

from .basecommand import BaseCommand
from grabdeps.cache import cache_root


class DepsCacheDirCommand(BaseCommand):
  def __init__(self):
    super().__init__(
      name="deps_cache_dir",
      desc="Print the current cache dir for dependencies and exit",
    )

  def run(self, args, output: Optional[TextIO] = None) -> int:
    if output:
      output.write(f"{cache_root()}\n")
    return 0


command = DepsCacheDirCommand()
