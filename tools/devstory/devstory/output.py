import colorama

from devstory.common import current_context

colorama.init(autoreset=True)

INFO_STYLE = colorama.Style.BRIGHT + colorama.Fore.MAGENTA
WARN_STYLE = colorama.Style.BRIGHT + colorama.Fore.YELLOW
ERR_STYLE = colorama.Style.BRIGHT + colorama.Fore.RED
SUCCESS_STYLE = colorama.Style.BRIGHT + colorama.Fore.GREEN
TRACE_STYLE = colorama.Style.BRIGHT + colorama.Fore.CYAN


def _print(style, text, prefix):
  print(style + "{0} ".format(prefix), end="")
  print(text)


def info(text, style=INFO_STYLE, tool="ds"):
  if not current_context().quite:
    _print(style, text, "[{0}] info ".format(tool))


def warn(text, style=WARN_STYLE, tool="ds"):
  _print(style, text, "[{0}] warn ".format(tool))


def error(text, style=ERR_STYLE, tool="ds"):
  _print(style, text, "[{0}] error".format(tool))


def done(text, style=SUCCESS_STYLE, tool="ds"):
  if not current_context().quite:
    _print(style, text, "[{0}] done ".format(tool))


def trace(text, style=TRACE_STYLE, tool="ds"):
  if current_context().verbose:
    _print(style, text, "[{0}] trace".format(tool))
