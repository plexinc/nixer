from typing import TextIO, List, Optional
from .basecommand import BaseCommand

from grabdeps.toolchain import get_toolchain_path, download_toolchain


class PathCommand(BaseCommand):
  def __init__(self):
    super().__init__(
      name="path", desc="Prints the absolute path to the current toolchain"
    )

  def run(self, args, output: Optional[TextIO] = None) -> int:
    toolchain_path = download_toolchain("https://artifacts.plex.tv/clang-plex")
    if output:
      output.write(f"{toolchain_path}\n")
    return 0


command = PathCommand()
