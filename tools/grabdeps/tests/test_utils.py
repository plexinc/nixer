import os

from grabdeps.utils import should_print_progressbar
from nose2.tools.decorators import with_setup


def setup():
  try:
    del os.environ["GRABDEPS_DISABLE_PROGRESSBAR"]
  except KeyError:
    pass

  try:
    del os.environ["BUILD_NUMBER"]
  except KeyError:
    pass


@with_setup(setup)
def test_disabling_because_ci_run():
  os.environ["BUILD_NUMBER"] = "2345"
  assert should_print_progressbar() == False


@with_setup(setup)
def test_disabling_because_explicitly_disabled():
  os.environ["GRABDEPS_DISABLE_PROGRESSBAR"] = "1"
  assert should_print_progressbar() == False


@with_setup(setup)
def test_disabling_both_conditions():
  os.environ["GRABDEPS_DISABLE_PROGRESSBAR"] = "1"
  os.environ["BUILD_NUMBER"] = "2345"
  assert should_print_progressbar() == False


@with_setup(setup)
def test_not_disabling_when_var_is_not_1():
  os.environ["GRABDEPS_DISABLE_PROGRESSBAR"] = "0"
  assert should_print_progressbar() == True
