from argparse import ArgumentParser
from textwrap import TextWrapper
from abc import abstractmethod, ABC
from typing import TextIO, List, Optional


class BaseCommand(ABC):
  def __init__(self, name, desc):
    self.name = name
    self.parser = ArgumentParser(description=desc)
    prog = self.parser.prog
    self.parser.prog = f"{prog} {self.name}"

  def __call__(self, args: List[str], output: Optional[TextIO] = None):
    parsed_args = self.parser.parse_args(args)
    return self.run(parsed_args, output)

  def format_help(self):
    wrapper = TextWrapper()
    lines = wrapper.wrap(f"  {self.name:16}{self.parser.description}")
    first, rest = lines[0], lines[1:]
    final = [first]
    for line in rest:
      final.append(" " * 18 + line)
    return "\n".join(final)

  @abstractmethod
  def run(self, args, output: Optional[TextIO] = None) -> int:
    """Runs the command logic.

    Args:
        args (List[str]): list of arguments to forward to argparse.
        output (TextIO): the output where plumbing output is written.

    Returns:
        int: [description]
    """
    pass
