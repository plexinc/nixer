import contextlib
import enum
import hashlib
import os
import platform
import shutil
import subprocess as sp
import sys
from functools import lru_cache
from pathlib import Path

import click
import pkg_resources
from yaspin import yaspin
from yaspin.spinners import Spinners

from devstory.env import halo_enabled, hide_subprocess_output

from .config import DsConfig


class CommandResult(enum.Enum):
  Success = 0
  Warning = 1
  Error = 2


INFO_FILE = ".ds_info"


@contextlib.contextmanager
def work_dir(path, remove=False):
  """Changes working directory and returns to previous on exit."""
  prev_cwd = Path.cwd()
  os.chdir(path)
  try:
    yield
  finally:
    os.chdir(prev_cwd)
    if remove:
      from shutil import rmtree

      rmtree(path, ignore_errors=True)


@contextlib.contextmanager
def ds_halo(text=""):
  if halo_enabled():
    with yaspin(Spinners.dots, text=text).cyan:
      yield
  else:
    yield


def run_command(cmd, status="", shell=False, env=None):
  from devstory import output

  """
  Runs a command.
    :param cmd: Command to run as a list.
    :returns: the returncode of the command.
  """
  _env = os.environ.copy()
  if env:
    _env.update(env)
  ctx = current_context()
  if not hide_subprocess_output():
    output.trace("Running command: " + " ".join(cmd))
    result = sp.run(cmd, env=_env)
  else:

    def run_it():
      return sp.run(cmd, env=_env, stdout=sp.PIPE, stderr=sp.STDOUT, shell=shell)

    if not ctx.quite:
      with ds_halo(text=status):
        result = run_it()
    else:
      result = run_it()

  ret = result.returncode

  if ctx.verbose:
    output.trace("Command returned: " + str(ret))

  NO_ERROR = 0
  if ret != NO_ERROR:
    from tempfile import NamedTemporaryFile

    output.error(f"Process returned with error {ret}")
    if result.stdout:
      print(result.stdout.decode(), end="")
      output.error("End of process output")
      with NamedTemporaryFile(delete=False) as temp:
        temp.write(result.stdout)
        output.info(f"Process output saved to {temp.name}")
  return ret


def get_wrapper_path():
  from devstory import output

  ctx = current_context()
  envwrap = ctx.home / "envwrap.py"
  if not envwrap.exists():
    output.error("envwrap.py does not exist! Did you run `ds bootstrap`?")
    return None
  return envwrap


"""
Find a binary under envwrap, requires bootstrap first
"""


def wrapped_which(binary):
  wrap = get_wrapper_path()
  if not wrap:
    return None

  from importlib.util import module_from_spec, spec_from_file_location

  spec = spec_from_file_location("envwrap", wrap.resolve())
  wrapmodule = module_from_spec(spec)
  spec.loader.exec_module(wrapmodule)

  return Path(wrapmodule.which(binary))


def wrapped_run(cmd, status="", dry_run=False):
  from devstory import output

  if using_new_toolchain():
    wrapped = ["plexec", *cmd]
  else:
    envwrap = get_wrapper_path()
    wrapped = [sys.executable, str(envwrap), *cmd]

  if dry_run:
    output.info(f"{' '.join(wrapped)}")
    return 0
  return run_command(wrapped, status)


def select_menu(prompt, options, default=None, select_default=False):
  from colorama import Style

  from devstory import output

  default_choice = None
  if select_default and default in options:
    output.info(f"Selecting {default} (--default)")
    return options.index(default)

  for idx, opt in enumerate(options):
    print(Style.BRIGHT + "{0}. ".format(idx + 1), end="")
    print(opt)

  if default in options:
    default_choice = options.index(default) + 1
    prompt = "{0} [default={1}]".format(prompt, default_choice)

  prompt += ": "

  while True:
    raw_choice = input(prompt)
    if not raw_choice and default in options:
      choice = default_choice
    else:
      try:
        choice = int(raw_choice)
      except ValueError:
        choice = -1

    if choice not in range(1, len(options) + 1):
      output.error(
        "Please choose a number in the range " "[1, {0}]".format(len(options))
      )
      continue
    break
  return choice - 1


def is_windows():
  return platform.system() == "Windows"


def conan_bin_name():
  ext = ".py" if is_windows() else ""
  return "conan-bin" + ext


class DsContext:
  def __init__(self):
    import pathlib

    self.verbose = False
    self.quite = False
    self.home = pathlib.Path().cwd()
    self.stored_flags = {}


pass_context = click.make_pass_decorator(DsContext, ensure=True)

_default_context = DsContext()


def current_context():
  try:
    return click.get_current_context().obj
  except RuntimeError:
    return _default_context


def get_conan_path():
  from devstory import output

  ctx = current_context()
  test = (
    Path(conan_bin_name()),
    get_project_dir() / conan_bin_name(),
    ctx.home / conan_bin_name(),
  )

  for test_dir in test:
    if test_dir.exists():
      return test_dir

  output.error("Failed to find conan-bin. Did you run ds bootstrap?")
  return None


def get_profiles_dir():
  ctx = current_context()
  test = (
    Path("profiles").absolute(),
    (ctx.home / Path("profiles")).absolute(),
    (get_project_dir() / Path("profiles")).absolute(),
  )

  for test_dir in test:
    if test_dir.is_dir():
      return test_dir

  return None


def get_info_file():
  return DsConfig(get_info_file_path())


def get_info_file_path():
  profiles_dir = get_profiles_dir()
  if profiles_dir:
    return str(get_profiles_dir() / INFO_FILE)
  return None


def get_project_dir(indicators=None):
  """Tries to determine the project directory in relation to the working dir"""

  def find_up(path):
    last_dir = Path(".").resolve()
    current_dir = last_dir
    while True:
      full_path = current_dir / path
      if full_path.exists():
        return full_path
      # pylint is wrong about this:
      #
      #     E1101:Instance of 'PurePath' has no 'resolve' member
      #
      # https://github.com/PyCQA/pylint/issues/224
      # pylint: disable=E1101
      last_dir = current_dir.resolve()
      current_dir = Path(current_dir / "..").resolve()
      if last_dir == current_dir:
        return None

  project_root_indicators = indicators or (".git", "conanfile.py", "conanfile.txt")
  for indicator in project_root_indicators:
    path = find_up(indicator)
    if path:
      return path.parents[0]
  raise RuntimeError(
    "Could not determine project root dir. Maybe you "
    "need to add an item to the `project_root_indicators`"
  )


def using_new_toolchain():
  plex_dev = DsConfig.load_plex_dev()
  llvm_toolchain = plex_dev.load_setting("tools", "llvm_toolchain")
  return llvm_toolchain is not None


def get_native_profile(debug=True):
  from devstory import output
  from devstory.profile import Profile

  plex_dev = DsConfig.load_plex_dev()
  profiles = get_profiles_dir().resolve()
  suffix = "debug" if debug else "release"

  conf_pr = plex_dev.load_setting("project", "native_profile")
  if conf_pr:
    conf_pr = profiles / f"{conf_pr}-{suffix}"
    output.trace(f"Checking native_profile from config: {conf_pr}")
    if conf_pr.exists():
      return Profile(conf_pr)
    output.warn(
      f"Configured profile from .plex_dev ({conf_pr.name}) does " "not exist!"
    )

  native_profile = {
    "Linux": "plex-linux-x86_64-clang-libstdcxx",
    "Darwin": "plex-macos-x86_64-clang-libcxx",
    "FreeBSD": "plex-freebsd-x86_64-clang-libcxx",
    # "Windows" ---> see below
  }

  # support new profile names
  system = platform.system()
  if system in ["Darwin", "Linux"]:
    prpath = profiles / native_profile[system]
    if not prpath.exists():
      native_profile[system] += f"-{suffix}"

  # On Windows, we have a bit of legacy. Earlier the mingw_msvc profiles
  # were generated, but only in the PMS dir. This changed because those
  # profiles are now static. However, in projects that are not PMS, but use
  # an old profiles ref, this would cause an error.
  mingw_msvc_profile = profiles / f"plex-windows-x86-mingw_msvc14-{suffix}"
  if mingw_msvc_profile.exists():
    native_profile["Windows"] = mingw_msvc_profile.name
  else:
    native_profile["Windows"] = f"plex-windows-x86_64-msvc15-{suffix}"

  if not system in native_profile:
    output.error(f"Sorry we have never tested this script on: {system}")
    return CommandResult.Error

  profile = native_profile[system]
  return Profile(profiles / Path(profile))


def _get_viable_profiles():
  from devstory.profile import Profile

  """
  Here we return a list of profiles that are available
  per platform. This list is explicit because of the
  hard rules there are coupled with the non-conformity
  to a standard of the file names.
  """
  viable_targets = {
    "Darwin": [
      "plex-macos-x86_64-clang-libcxx-debug",
      "plex-macos-x86_64-clang-libcxx-release",
      "plex-macos-x86_64-clang-libcxx",
      "plex-ios-x86_64-clang-libcxx-debug",
      "plex-ios-x86_64-clang-libcxx-release",
      "plex-ios-x86_64-clang-libcxx",
      "plex-ios-armv7-clang-libcxx",
      "plex-ios-aarch64-clang-libcxx",
    ],
    "Windows": [
      "plex-windows-x86-mingw_msvc14-release",
      "plex-windows-x86-mingw_msvc14-debug",
      "plex-windows-x86_64-msvc15-debug",
      "plex-windows-x86_64-msvc15-release",
    ],
    "Linux": [
      "plex-linux-x86_64-clang-libstdcxx-release",
      "plex-linux-x86_64-clang-libstdcxx-debug",
      "plex-linux-x86_64-clang-libstdcxx",
      "plex-linux-x86-clang-libstdcxx",
      "plex-linux-armv7hf-clang-libstdcxx",
      "plex-linux-aarch64-clang-libstdcxx",
      "plex-linux-armv7sf-clang-libstdcxx",
      "plex-linux-armv7hf-sysv-clang-libstdcxx",
      # new android profiles
      "plex-android-aarch64-clang-libcxx-debug",
      "plex-android-aarch64-clang-libcxx-release",
      "plex-android-armv7-clang-libcxx-debug",
      "plex-android-armv7-clang-libcxx-release",
      "plex-android-x86-clang-libcxx-debug",
      "plex-android-x86-clang-libcxx-release",
      "plex-android-x86_64-clang-libcxx-debug",
      "plex-android-x86_64-clang-libcxx-release",
      # old android profiles
      "plex-android-aarch64-clang-libstdcxx-release",
      "plex-android-aarch64-clang-libstdcxx-debug",
      "plex-android-x86_64-clang-libstdcxx-debug",
      "plex-android-x86_64-clang-libstdcxx-release",
      "plex-android-aarch64-clang-libstdcxx",
      "plex-android-armv7-clang-libstdcxx",
      "plex-android-x86-clang-libstdcxx",
      "plex-mingw32-x86-gcc63-libstdcxx",
    ],
    "FreeBSD": ["plex-freebsd-x86_64-clang-libcxx"],
  }

  plex_dev = DsConfig.load_plex_dev()

  config_profiles = plex_dev.load_list_setting("project", "profiles")
  profile_names = config_profiles or viable_targets.get(platform.system(), [])

  viable = [
    Profile(get_profiles_dir() / pro)
    for pro in profile_names
    if (get_profiles_dir() / pro).exists()
  ]

  if not viable:
    raise RuntimeError(
      "The list of viable profiles is empty! " "Please report this in #conan!"
    )
  return sorted(viable)


def get_all_viable_profiles():
  return _get_viable_profiles()


def _get_variations_from_profile(profile):
  if using_new_toolchain():
    plex_dev = DsConfig.load_plex_dev()
    project_variants = plex_dev.load_list_setting(
      "project", "variants", ["standard", "nano", "desktop"]
    )
    return project_variants

  profiles_path = profile.path.parents[0]

  import importlib.util

  spec = importlib.util.spec_from_file_location(
    "profiles.profile_variants", profiles_path / "profile_variants.py"
  )
  profile_variants = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(profile_variants)

  plex_dev = DsConfig.load_plex_dev()
  project_variants = plex_dev.load_list_setting(
    "project", "variants", ["standard", "nano", "desktop"]
  )

  variants = profile_variants.profile_variants.get(profile.name, [])
  filtered_variants = [var for var in variants if var in project_variants]
  if not filtered_variants:
    from devstory import output

    output.info(
      f"Couldn't find any valid variations for {profile} - defaulting to standard"
    )
    # if we don't find any variants - just assume standard
    return ["standard"]
  return filtered_variants


@lru_cache(maxsize=1)
def get_toolchain_path() -> Path:
  from devstory import output

  proc = sp.run(["plexec", "--print-env", "PLEX_TOOLCHAIN_PATH"], stdout=sp.PIPE)
  if proc.returncode != 0:
    raise RuntimeError("Failed to run pconan to find the toolchain!")

  path = proc.stdout.decode().strip()
  output.info(f"Toolchain path: {path}")
  return Path(path)


def verify_new_toolchain():
  with ds_halo("Updating / verifying toolchain ..."):
    sp.run(["plexec"], stdout=sp.PIPE, check=True)

  path = get_toolchain_path()
  if not path.is_dir():
    raise RuntimeError(f"Toolchain not available at {path}!")


def get_toolchain_files():
  toolchain_path = get_toolchain_path()
  toolchains = []
  plex_dev = DsConfig.load_plex_dev()
  project_toolchains = plex_dev.load_list_setting("project", "toolchains", [])
  for toolchain_file in (toolchain_path / "toolchains").iterdir():
    if toolchain_file.is_file() and toolchain_file.suffix == ".cmake":
      if project_toolchains:
        if toolchain_file.name in project_toolchains:
          toolchains.append(toolchain_file)
      else:
        toolchains.append(toolchain_file)

  return sorted(toolchains)


def select_toolchain_file(select_default=False):
  from devstory import output

  toolchains = get_toolchain_files()
  output.info("Selecting toolchain")
  last = default_toolchain()
  last_toolchain = next((p for p in toolchains if p.name == last.name), None)
  toolchain_name = last_toolchain.name if last_toolchain else None
  selected_idx = select_menu(
    "Please choose a toolchain file",
    [x.name for x in toolchains],
    default=toolchain_name,
    select_default=select_default,
  )
  selected_toolchain = toolchains[selected_idx]

  DsConfig().save_setting("recent", "toolchain", selected_toolchain.name)

  return selected_toolchain


def get_toolchain_from_cache():
  cmake_cache = Path("CMakeCache.txt")
  if cmake_cache.is_file():
    cache_data = cmake_cache.read_text()
    for lne in cache_data.split():
      if lne.startswith("CMAKE_TOOLCHAIN_FILE"):
        return Path(lne.split("=")[1].strip())
  return None


def select_profile(name=None, select_default=False):
  profiles = _get_viable_profiles()
  if name:
    from devstory.profile import load_profile_by_name

    selected_profile = load_profile_by_name(name)
  else:
    from devstory import output

    output.info("Selecting profile")
    last = default_profile()
    last_profile = next((p for p in profiles if p.name == last.name), None)
    selected_idx = select_menu(
      "Please choose a profile",
      profiles,
      default=last_profile,
      select_default=select_default,
    )
    selected_profile = profiles[selected_idx]

  DsConfig().save_setting("recent", "profile", selected_profile.name)

  return selected_profile


def default_profile():
  profiles = _get_viable_profiles()

  last = DsConfig().load_setting("recent", "profile")
  if not last:
    last = get_native_profile().name

  def_profile = next((p for p in profiles if p.name == last), None)
  if not def_profile:
    return get_native_profile()

  return def_profile


def default_toolchain():
  toolchains = get_toolchain_files()

  platform_toolchains = {
    "Darwin": "x86_64-apple-darwin-macos",
    "Windows": "i686-windows-msvc",
  }
  def_toolchain_file = "x86_64-linux-musl"

  system_name = platform.system()
  def_toolchain_file = platform_toolchains.get(system_name, None)

  last = DsConfig().load_setting("recent", "toolchain")
  if not last:
    last = get_toolchain_path() / f"{def_toolchain_file}.cmake"
  else:
    last = get_toolchain_path() / last

  def_profile = next((p for p in toolchains if p.name == last.name), None)
  if not def_profile:
    return get_toolchain_path() / f"{def_toolchain_file}.cmake"

  return def_profile


def select_build_type(selected_toolchain: Path, select_default=False):
  from devstory import output

  output.info("Selecting build type")

  plex_dev = DsConfig.load_plex_dev()
  buildtype_from_pd = plex_dev.load_setting("project", "default_buildtype")
  if buildtype_from_pd:
    return buildtype_from_pd

  config = DsConfig()
  last = config.load_setting("recent", "buildtype_" + selected_toolchain.name)

  build_types = ["Debug", "RelWithDebInfo"]
  last_variation = next((p for p in build_types if p == last), "Debug")
  selected_buildtype = build_types[0]
  if len(build_types) > 1:
    selected_idx = select_menu(
      "Please choose a build type",
      build_types,
      default=last_variation,
      select_default=select_default,
    )
    selected_buildtype = build_types[selected_idx]
  config.save_setting(
    "recent", "buildtype_" + selected_toolchain.name, selected_buildtype
  )

  return selected_buildtype


def get_new_toolchain_cmake_options(select_default=False):
  toolchain = select_toolchain_file(select_default=select_default)
  variation = select_variation(toolchain, select_default=select_default)
  build_type = select_build_type(toolchain, select_default=select_default)
  plex_dev = DsConfig.load_plex_dev()
  variant_key = plex_dev.load_setting(
    "project", "variant_key", "PLEX_MEDIA_SERVER_VARIATION"
  )

  cmake_options = [
    f"-DCMAKE_BUILD_TYPE={build_type}",
    f"-D{variant_key}={variation}",
    f"-DCMAKE_TOOLCHAIN_FILE={str(toolchain)}",
    "-Wno-dev",
  ]

  return cmake_options, toolchain


def select_variation(selected_profile, select_default=False):
  from devstory import output

  output.info("Selecting variation")

  plex_dev = DsConfig.load_plex_dev()
  variant_from_plex_dev = plex_dev.load_setting("project", "default_variant")
  if variant_from_plex_dev:
    return variant_from_plex_dev

  config = DsConfig()
  last = config.load_setting("recent", "variation_" + selected_profile.name)

  variations = _get_variations_from_profile(selected_profile)
  last_variation = next((p for p in variations if p == last), "Standard")
  selected_variation = variations[0]
  if len(variations) > 1:
    selected_idx = select_menu(
      "Please choose a variation",
      variations,
      default=last_variation,
      select_default=select_default,
    )
    selected_variation = variations[selected_idx]
  config.save_setting(
    "recent", "variation_" + selected_profile.name, selected_variation
  )

  return selected_variation


def get_ds_version():
  from importlib_metadata import version, PackageNotFoundError

  try:
    return version("devstory")
  except PackageNotFoundError:
    return "unknown"


def get_ds_latest_version():
  from distutils.version import StrictVersion
  from devstory.artifactory import Artifactory

  rt = Artifactory.default()
  try:
    resp = rt.get(
      "/search/prop",
      headers={"X-Result-Detail": "properties"},
      params={"pypi.name": "devstory"},
    ).json()["results"]
    versions = []
    for d in resp:
      try:
        versions.append(StrictVersion(d["properties"]["pypi.version"][0]))
      except ValueError:
        # only consider stable versions
        pass
    versions.sort()
    if versions:
      return str(versions[-1])
  except KeyError:
    # Sometimes Artifactory returns an error especially since they introduced lockout
    # for tokens. Let's assume there is no update if we couldn't parse the data
    pass
  default_low_version = "1.0.0"
  return default_low_version


def check_for_update():
  try:
    from distutils.version import StrictVersion

    current_version = StrictVersion(get_ds_version())
    latest_version = StrictVersion(get_ds_latest_version())
    return latest_version > current_version, current_version, latest_version
  except ValueError:
    return False, StrictVersion("1.0.0"), StrictVersion("1.0.0")


def is_64bit_interpreter():
  # This is the most reliable way to check the interpreter bitness
  # because universal binaries on macOS may run in 32 bit mode.
  # https://docs.python.org/2/library/platform.html#platform.architecture
  # https://stackoverflow.com/a/1842699/140367
  return sys.maxsize > 2 ** 32


def resource_filename(res_name: str):
  return pkg_resources.resource_filename("devstory.resources", res_name)


def resource_string(res_name: str):
  data = pkg_resources.resource_string("devstory.resources", res_name)
  return data.decode("utf-8")


def copy_resource(res_name: str, target: str):
  shutil.copy(resource_filename(res_name), target)


def get_git_branch_name():
  res = sp.run(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    stdout=sp.PIPE,
    stderr=sp.PIPE,
  )
  if res.returncode != 0:
    return None

  return res.stdout.decode().strip()


def is_truthy(expression):
  # Return if the expression could be considered true in many different ways
  return expression and str(expression).lower() in ("1", "on", "true", "yes", "y")


def get_sha256(filename, extra_data: str = None):
  h = hashlib.sha256()
  b = bytearray(1024 * h.block_size)
  mv = memoryview(b)
  with open(filename, "rb", buffering=0) as f:
    for n in iter(lambda: f.readinto(mv), 0):
      h.update(mv[:n])
  if extra_data:
    h.update(extra_data.encode())
  return h.hexdigest()


def is_cmake_deps():
  # return true if cmake installs deps (tarball deps)
  plex_dev = DsConfig.load_plex_dev()
  return is_truthy(
    plex_dev.load_setting("project", "cmake_installs_deps")
  ) or plex_dev.has_setting("tools", "llvm_toolchain")


def get_terminal_link(url, text=None):
  if not text:
    text = url
  return f"\u001b]8;;{url}\u001b\\{text}\u001b]8;;\u001b\\"
