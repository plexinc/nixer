from typing import TextIO, List, Optional
from .basecommand import BaseCommand

from grabdeps.toolchain import download_toolchain, get_toolchain_path


class FetchCommand(BaseCommand):
  def __init__(self):
    super().__init__(name="fetch", desc="Fetches the current toolchain version")
    self.parser.add_argument(
      "-o",
      "--output-dir",
      default=None,
      help="Where to extract the dependencies. Can be an absolute or relative path.",
    )
    self.parser.add_argument(
      "-u",
      "--url",
      default="https://artifacts.plex.tv/clang-plex",
      help="Where to download dependencies from",
    )
    self.parser.add_argument(
      "-v",
      "--version",
      default=None,
      help="Toolchain version, overriden from .plex_dev",
    )

  def run(self, args, output: Optional[TextIO] = None) -> int:
    download_toolchain(args.url, args.version, args.output_dir)
    return 0


command = FetchCommand()
