""" Module responsible for running all conan commands """
import os
import sys

from conans.model.profile import Profile
from conans import tools

from beard.depbuilder import CRunner as CR


class OutputBuffer(object):  #pylint: disable=too-few-public-methods
  """ Our buffer method """

  def __init__(self):
    self.buffer = []

  def write(self, buf):
    """ write function """
    self.buffer.append(buf.strip())


class ConanRunner(object):
  """ This is the class that invokes all the conan commands """
  cmds_with_profile = ("test", "build", "install", "info", "create")
  cmds_with_settings = ()

  def __init__(self, rootpath, options):
    """
    :type rootpath: str
    """
    self.rootpath = rootpath
    self.options = options
    self.runner = CR()
    self.profile_path = self.get_profile()
    self.buildinfo_path = os.path.join(self.rootpath, "buildinfo.json")

  def get_profile(self):
    if not self.options.profile:
      return "default"

    profile = os.path.join(self.rootpath, "profiles", self.options.profile)

    if not os.path.exists(profile):
      print("ERROR: profile {0} is not available!".format(profile))
      return None

    return profile

  def _run_command(self, cmd, args=None, output=True, cwd=None):
    """ helper method that runs the actual command """
    cmdargs = args if args is not None else ""
    if cmd in self.cmds_with_profile:
      cmdargs += " --profile {0}".format(
          os.path.join(self.rootpath, "profiles", self.profile_path))
    elif cmd in self.cmds_with_settings:
      with open(self.profile_path, "r") as pdata:
        profile = Profile.loads(pdata.read())
        for setting in profile.settings:
          cmdargs += " -s{0}={1}".format(setting[0], setting[1])

    # figure out which conan binary to use:
    #    1) check $PLEX_CONAN_PATH
    #    2) check if there is a conan-bin next to this script
    #    3) fallback to "conan"

    conan_bin_path = os.path.join(self.rootpath, "conan-bin")
    conan = os.environ.get("PLEX_CONAN_PATH", None)
    if not conan:
      if os.path.isfile(conan_bin_path):
        conan = conan_bin_path
      elif os.path.isfile(conan_bin_path + ".py"):
        conan = conan_bin_path + ".py"
      else:
        conan = "conan"

    with tools.environment_append(self._conan_environment()):
      finalcmd = "\"{python}\" {0} {1} {2}".format(
          conan,
          cmd if cmd is not None else "",
          cmdargs if cmdargs is not None else "",
          python=sys.executable)
      print(finalcmd)
      return self.runner(finalcmd, output, cwd=cwd)

  def export_package(self, pkgname, variant=False, namespace=None):
    """ exports a specific package """
    if not namespace:
      namespace = self.options.namespace
    package_path = os.path.join(self.rootpath, "packages"
                                if not variant else "variants", pkgname)
    ret = self._run_command("export", '"{}" "{}"'.format(
        package_path, namespace))
    return ret is 0

  @staticmethod
  def _conan_user_home():
    """ returns the CONAN_USER_HOME """
    return os.environ.get("CONAN_USER_HOME", os.path.expanduser("~").strip())

  def _conan_environment(self):
    return {
        "CONAN_USER_HOME": self._conan_user_home(),
        "CONAN_RECIPE_LINTER": "False",
        "CONAN_USERNAME": os.getenv("CONAN_USERNAME", "plex"),
        "CONAN_CHANNEL": os.getenv("CONAN_CHANNEL", "stable")
    }

  def build_order(self, package, query="ALL"):
    """ Return the build order from a conanfile """
    buf = OutputBuffer()

    path = None
    paths = [
        os.path.join(self.rootpath, "variants", package, "conanfile.py"),
        os.path.join(self.rootpath, "variants", package, "conanfile.txt"),
        os.path.join(self.rootpath, "packages", package, "conanfile.txt"),
        os.path.join(self.rootpath, "packages", package, "conanfile.py")
    ]

    for ppath in paths:
      if os.path.exists(ppath):
        path = ppath
        break

    if not path:
      print("Failed to find package {0}".format(package))
      return []

    output = self._run_command(
        "info", "{} -bo {}".format(os.path.dirname(path), query), output=buf)

    if output is not 0:
      print("Failed to get builder from variant: {0}\n{1}".format(
          package, "\n".join(buf.buffer)))
      return []

    if not buf.buffer:
      print("Failed to get build_orders from variant!")
      return []

    build_buffer = None
    # find first line starting with [
    for l in buf.buffer:
      if l[0] == '[':
        build_buffer = l.strip()

    if not build_buffer:
      return []

    packages = []
    for line in buf.buffer:
      if line.startswith("["):
        packages += [
            a[:a.index("]")].split(", ") for a in line.split("[") if len(a) > 0
        ]

    return packages

  def test_package(self, ref, export=True, build="missing", options=""):
    """ Run conan test_package on a specific package """
    if "@" in ref:
      name = ref.split("/")[0]
    else:
      name = ref

    pdir = os.path.join(self.rootpath, "packages", name, "test_package")

    if not os.path.isdir(pdir):
      print(f"{name}: is missing test_package folder! {pdir}")
      return False

    arg_lst = [pdir, ref, "--build=" + build]

    if options:
      arg_lst.extend(options.split(" "))
    args = " ".join(arg_lst)

    print("Testing package {0} with arguments {1}".format(name, args))
    if self._run_command(
        "test", args, output=(not self.options.quietbuild)) is not 0:
      print("FAILED TO BUILD AND TEST PACKAGE {0}".format(name))
      return False

    return True

  def upload_package(self,
                     packageref,
                     binaries=True,
                     force=False,
                     package_id=None):
    """ run conan upload on a package """
    success = True

    upload_args = "-r {remote} -no all {ref} {all} {pkgid}".format(
        remote=self.options.remote,
        ref=packageref,
        all="--all" if binaries and not package_id else "",
        pkgid=f"-p {package_id}" if package_id else "")

    if self._run_command("upload", upload_args, output=True) is not 0:
      print("FAILED TO UPLOAD {0}".format(packageref))
      success = False

    return success

  def source_package(self, name):
    """ Run conan source on a package """
    if self._run_command("source", "-f {0}".format(name)) is not 0:
      print("Failed to SOURCE package {0}".format(name))
      return False
    return True

  def remove_package(self, package, source=True, build=True, binary=False):
    """ Run conan remove on a package """
    if ";" in package:
      package = package.split(";")[0]
    components = "{0}{1}{2}".format("-b " if build else "", "-s "
                                    if source else "", "-p " if binary else "")
    if self._run_command("remove", "-f {0} {1}".format(components,
                                                       package)) is not 0:
      print("Failed to REMOVE package {0}".format(package))
      return False
    return True

  def search_all(self, remote, filter_namespace=True):
    """ run conan search and return all packages"""
    searcharg = "-r {0}".format(remote)
    if remote == "local":
      searcharg = ""

    buf = OutputBuffer()
    if self._run_command("search", searcharg, output=buf) is not 0:
      print("FAILED TO SEARCH REMOTE {0}: {1}".format(remote,
                                                      "\n".join(buf.buffer)))
      return []

    namespace = "@"
    if filter_namespace:
      namespace += self.options.namespace

    return [a for a in buf.buffer if namespace in a]

  def install(self, param, build="missing", update=False):
    """ run conan install on a conanfile """
    from .buildinfoparser import parse_buildinfo

    args = "{0} --build={1} --json {2}".format(param, build,
                                               self.buildinfo_path)
    if update:
      args += " --update"

    status = self._run_command("install", args)
    SUCCESS = 0
    if status != SUCCESS:
      raise RuntimeError(
          f"conan install returned a non-zero status code: {status}")
    info = parse_buildinfo(self.buildinfo_path)

    return info
