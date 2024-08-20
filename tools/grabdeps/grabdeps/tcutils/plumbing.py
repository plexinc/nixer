import sys
import io
from argparse import ArgumentParser, REMAINDER
from importlib import import_module
from contextlib import redirect_stdout
from sys import argv


class ToolchainPlumbing(ArgumentParser):
  commands = ["fetch", "path", "deps_cache_dir"]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.add_argument("command")
    self.all_commands = self.load_all("grabdeps.tcutils.commands")

  def load_all(self, module_name):
    all_commands = {}
    for cmd in self.commands:
      mod = import_module(f"{module_name}.{cmd}")
      all_commands[cmd] = mod.command
    return all_commands

  def print_help(self):
    super().print_help(sys.stdout)
    print("\ncommands:")
    for cmd in self.all_commands.values():
      print(cmd.format_help(), end="\n\n")

  def run_command(self, cmd, args) -> int:
    if cmd not in self.commands:
      print("No such command.")
      return 1
    command = self.all_commands[cmd]
    if "-h" in args or "--help" in args:
      result = command(args, None)
    else:
      result = 0
      plumbing_output = io.StringIO()
      # This redirect is used to silence all other output while plumbing_output will be
      # used for the deliberate output from the command.
      with redirect_stdout(io.StringIO()) as stdout:
        result = command(args, plumbing_output)
      print(plumbing_output.getvalue(), end="")
    return result

  def run(self) -> int:
    args = self.parse_args([argv[1]])
    rest = argv[2:]
    return self.run_command(args.command, rest)


def cli():
  ToolchainPlumbing().run()
