#! /usr/bin/env python3
import re
import sys

import click

from devstory.ds import cli

# pylint: disable=protected-access
click.core._verify_python3_env = lambda: None


def main():
  sys.argv[0] = re.sub(r"(-script\.pyw?|\.exe)?$", "", sys.argv[0])
  # pylint: disable=no-value-for-parameter
  # `cli` is a click callable because of the decorators so this is a
  # correct way to call it.
  sys.exit(cli())


if __name__ == "__main__":
  main()
