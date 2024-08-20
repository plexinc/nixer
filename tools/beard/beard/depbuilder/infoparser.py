""" parse a conanbuildinfo.txt file """
from collections import defaultdict

class InfoParser(object):
  """ our infoparser method """
  @staticmethod
  def get_options(filepath):
    """ get all options from the file """
    with open(filepath, "r") as filed:
      lines = filed.readlines()

      options = defaultdict(dict)
      pkglist = []
      full_options = False
      full_requires = False

      for line in lines:
        line = line.strip()

        if line == '[full_options]':
          full_options = True
          full_requires = False
          continue

        if line == '[full_requires]':
          full_requires = True
          full_options = False

        if full_options and line and ":" in line:
          key, valkey, valval = line.replace("=", ":").split(":")
          options[key][valkey] = valval
          continue

        if full_requires and line and "@plex/stable" in line:
          pkglist.append(line.split("/")[0])

        full_options = False

      return options, pkglist

  @staticmethod
  def get_options_str(options):
    """ get the options as a conan options string """
    optlist = ["-o{pkg}:{option}=\"{value}\"".format(pkg=pkg, option=option, value=value)
               for pkg, pkgopt in options.items()
               for option, value in pkgopt.items()]
    return " ".join(optlist)

if __name__ == '__main__':
  options, pkglist = InfoParser.get_options("conaninfo.txt")
  print(pkglist)
  print(InfoParser.get_options_str(options))
