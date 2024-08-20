from os import getenv


def halo_enabled():
  return getenv("DS_HALO_ENABLED", "1") == "1"


def hide_subprocess_output():
  return getenv("DS_HIDE_SUBPROCESS_OUTPUT", "0") == "1"
