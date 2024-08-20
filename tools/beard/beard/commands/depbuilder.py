from beard.common import Bunch
from beard.depbuilder.dep_builder import MainDepBuilder


def do_depbuilder(args):
  options = Bunch(args)
  depbuilder = MainDepBuilder(options)
  depbuilder.run()
