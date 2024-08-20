#!/usr/bin/env python3

import os
import platform
import re
import sys
from functools import lru_cache
from pathlib import Path
from shutil import which
from subprocess import PIPE, STDOUT, run

from grabdeps.cache import Cache
from grabdeps.downloader import Downloader
from grabdeps.resutils import get_resdir, iter_resdir_files
from grabdeps.toolchain import download_toolchain
from grabdeps.utils import (
    find_plex_dev,
    parse_plex_dev,
    save_cookie,
    short_circuit,
    verbose_display_python,
)

CONAN_ENV = os.environ.copy()

# Whenever you need to add a new remote in here make sure to update the
# remotes.txt and the config_version.txt file in the resources directory.
REMOTES = (
    "toolchain",
    "experimental",
    "test",
    "llvm",
    "main",
    "new",
)


def platform_name():
    pl_name = platform.system().lower()
    if "cygwin" in pl_name:
        # we want to use the windows pyz under cygwin
        return "windows"
    return pl_name


def pyver() -> str:
    # Clamp version to 3.7 since we don't build conan pyz for anything higher than that.
    vmajor, vminor = sys.version_info.major, min(7, sys.version_info.minor)
    return f"py{vmajor}{vminor}"


def conan_pyz_name(version):
    return f"conan-{version}-{platform_name()}-{pyver()}.pyz"


def prepend_env_var(envvar: str, str_to_prepend: str):
    oldvar = CONAN_ENV.get(envvar, "")
    if oldvar:
        newval = f"{str_to_prepend}{os.pathsep}{oldvar}"
    else:
        newval = str_to_prepend
    CONAN_ENV[envvar] = newval


# Figure out what we will set CONAN_USER_HOME to
# either we will leave it alone if CONAN_USER_HOME
# is already set, otherwise we will check if
# .plex_dev contains conan.home and use that as a
# subdir to $HOME/.conan_plex
#
def get_conan_user_home() -> Path:
    if "CONAN_USER_HOME" in CONAN_ENV:
        return Path(CONAN_ENV["CONAN_USER_HOME"])
    plex_dev = parse_plex_dev()
    conan_home = plex_dev.get("conan", "home", fallback=None)
    if conan_home:
        return Path.home() / ".conan_plex" / conan_home

    return Path.home() / ".conan_plex"


def process_env():
    rootpath = Path.cwd()
    # Find plex_dev path
    plex_dev = find_plex_dev()
    if plex_dev:
        rootpath = plex_dev.parent
        plex_conan_dir = os.getenv("PLEX_CONAN_DIR")
        if plex_conan_dir:
            plex_conan_dir = Path(plex_conan_dir)
            if plex_conan_dir.is_dir():
                prepend_env_var("PYTHONPATH", str(plex_conan_dir / "plexconantool"))
            else:
                print(
                    "WARNING: Environment variable PLEX_CONAN_DIR points to a non-existent path"
                )
        else:
            pct_dir_candidates = (
                rootpath / "plexconantool",
                rootpath / ".." / "plex-conan" / "plexconantool",
                rootpath / ".." / "conan" / "plexconantool",
                rootpath / ".." / ".." / "plex-conan" / "plexconantool",
                rootpath / ".." / ".." / "conan" / "plexconantool",
            )
            for candidate in pct_dir_candidates:
                if candidate.is_dir():
                    prepend_env_var("PYTHONPATH", str(candidate))

    CONAN_ENV["CONAN_USER_HOME"] = str(get_conan_user_home())
    CONAN_ENV["ARTIFACTORY_USER"] = os.getenv("PLEX_ARTIFACTORY_USER", ">")
    CONAN_ENV["ARTIFACTORY_PASSWORD"] = os.getenv("PLEX_ARTIFACTORY_TOKEN", ">")

    for remote in REMOTES:
        CONAN_ENV[f"CONAN_PASSWORD_{remote.upper()}"] = CONAN_ENV[
            "ARTIFACTORY_PASSWORD"
        ]
        CONAN_ENV[f"CONAN_LOGIN_USERNAME_{remote.upper()}"] = CONAN_ENV[
            "ARTIFACTORY_USER"
        ]

    CONAN_ENV["PLEX_CONAN_AUX_DIR"] = os.getenv(
        "PLEX_CONAN_AUX_DIR", str(rootpath / "aux-output")
    )

    def_user = "plex"
    def_channel = "stable"

    # check if we have user_channel in config
    plex_dev = parse_plex_dev()
    user_channel = plex_dev.get("bootstrap", "user_channel", fallback=None)
    if user_channel:
        def_user, def_channel = user_channel.split("/")

    # Always prefer CONAN_USERNAME/CHANNEL from environment.
    CONAN_ENV["CONAN_USERNAME"] = CONAN_ENV.get("CONAN_USERNAME", def_user)
    CONAN_ENV["CONAN_CHANNEL"] = CONAN_ENV.get("CONAN_CHANNEL", def_channel)


def conan_main(conan_path):
    from argparse import REMAINDER, ArgumentParser
    from signal import SIG_IGN, SIGINT, signal

    parser = ArgumentParser(description="conan wrap")
    parser.add_argument("command", nargs=REMAINDER, help="wrap me")
    args, rest = parser.parse_known_args()

    # Ignore SIGINT so that the subprocess actually handles it.
    signal(SIGINT, SIG_IGN)

    conan_cmd = []
    if using_reqs():
        conan_cmd = [str(conan_path)]
    else:
        conan_cmd = [sys.executable, str(conan_path)]

    import pprint

    pprint.pp([(k, v) for k, v in CONAN_ENV.items() if v is None])
    pprint.pp(CONAN_ENV)
    print("Running :", conan_cmd + rest + args.command)
    returncode = run(conan_cmd + rest + args.command, env=CONAN_ENV).returncode

    sys.exit(returncode)


# This methods checks if we need to install conan configuration
# It looks for a directory called "conan_config" next to .plex_dev
# if that's not found it will use the conan_config dir that's bundled
# with grabdeps.
#
# This function also implements basic version checking that will read
# config_version.txt from the folder above. If the contents of that file
# matches the content of the file installed this function will exit fast
# otherwise it will call conan config install and install the configuration
#
def install_conan_config(conan_path: Path):
    conan_home = get_conan_user_home()

    pd_path = find_plex_dev()
    conan_config_path = pd_path.parent / "conan_config" if pd_path else None
    if not conan_config_path or not conan_config_path.is_dir():
        conan_config_path = get_resdir("grabdeps.resources.conan_config")

    installed_conf = conan_home / ".conan" / "config_version.txt"
    config_ver = conan_config_path / "config_version.txt"
    expected_version = None
    actual_version = None

    if config_ver.is_file():
        expected_version = config_ver.read_text().strip()

    if installed_conf.is_file():
        actual_version = installed_conf.read_text().strip()
        if actual_version == expected_version:
            return

    print(
        f"Installing new version of conan configuration: {expected_version}, old: {actual_version}"
    )

    cmd = None
    if "pyz" in conan_path.name:
        cmd = [sys.executable, str(conan_path)]
    else:
        cmd = [str(conan_path)]

    cmd += ["config", "install", str(conan_config_path)]
    run(cmd, check=True, env=CONAN_ENV)


# This function returns True if the .plex_dev sets tools.conan to requriements
# which indicates that the wrapper should read the conan version out of
# requriements.txt instead of .plex_dev
#
@lru_cache()
def using_reqs() -> bool:
    plex_dev = parse_plex_dev()
    conan_ver_str = plex_dev.get("tools", "conan", fallback=None)
    if not conan_ver_str:
        print(
            "WARNING: No tools.conan entry in .plex_dev - falling back to system version!"
        )
        conan_ver_str = "requirements"

    if conan_ver_str == "requirements":
        pd_path = find_plex_dev()
        if (pd_path.parent / "requirements.txt").is_file():
            return True
        else:
            print(
                "WARNING: .plex_dev indicated we should use requirements.txt but there is no such file!"
            )

    return False


# Read conan version from either .plex_dev or requirements.txt
#
@lru_cache()
def conan_version() -> str:
    plex_dev = parse_plex_dev()
    conan_ver_str = plex_dev.get("tools", "conan", fallback=None)

    if using_reqs():
        pd_path = find_plex_dev()
        if not pd_path:
            print("ERROR: Couldn't find .plex_dev!")
            sys.exit(1)
        reqs = pd_path.parent / "requirements.txt"
        with open(reqs, "r") as rfd:
            for line in rfd:
                if "conan" in line and "==" in line:
                    ver = line.split("==")[1].strip()
                    return ver

            print(
                "ERROR: .plex_dev said we would find conan in requriements.txt - but it's not there!"
            )
            print(
                "Note that pconan ONLY handles conan==x.y.z - anything else is not going to be used."
            )
            sys.exit(1)

    return conan_ver_str


# Compare conan version from conan --version and what we get from
# conan_version above. This warns if the user is using a version
# of conan we don't really expect.
#
def check_conan_version(path: Path) -> bool:
    wanted_version = conan_version()

    res = run([path, "--version"], stdout=PIPE, check=True)
    match = re.match("Conan version (.*)$", res.stdout.decode())
    if not match:
        print(f"ERROR: failed to execute and get version from conan: {res.stdout}")
        sys.exit(1)

    actual_version = match.group(1)

    if wanted_version != actual_version:
        file = "requirements.txt" if using_reqs() else ".plex_dev"
        print(
            f"ERROR: {file} requested conan version {wanted_version} but {path} is {actual_version}"
        )
        if using_reqs():
            print("Try to re-install requirements: pip install -Ur requirements.txt")
        else:
            print(
                f"The pyz ({path}) contains the wrong version! That can't be good. Report to the build team!"
            )
        sys.exit(1)


# Download and cache the conan pyz file
#
def cache_pyz() -> Path:
    cache = Cache(f"conan-{pyver()}")

    conan_version_no_rev = conan_version().split("-")[0]

    if not short_circuit(conan_version(), cache.get_cache_dir(conan_version())):
        downloader = Downloader("https://artifacts.plex.tv/pyz-builds/conan", cache)
        downloader.download(
            f"{conan_version_no_rev}/{platform_name()}/{conan_pyz_name(conan_version())}",
            out_filename=f"{conan_version()}/{conan_pyz_name(conan_version())}",
        )
        save_cookie(conan_version(), cache.get_cache_dir(conan_version()))

    return cache.get_cache_dir(conan_version()) / conan_pyz_name(conan_version())


# Find the path to the conan binary. This will first check environment
# GRABDEPS_CONAN_COMMAND and use that if set.
#
# Otherwise we'll check if .plex_dev contains either "requirements" in which
# case we will check requirements.txt for the version and then check the path
# for the conan command.
#
# If .plex_dev contains a actual version number we try to find the pyz for that version
# from artifactory and use that instead.
def get_conan_path() -> Path:
    # plex_dev = parse_plex_dev()
    # path = None
    if "GRABDEPS_CONAN_COMMAND" in os.environ:
        print("heheheheheheh")
        p = Path(os.environ["GRABDEPS_CONAN_COMMAND"])
        if not p.exists():
            print(
                f"ERROR: GRABDEPS_CONAN_COMMAND was set to: '{os.getenv('GRABDEPS_CONAN_COMMAND')}' but I couldn't find it."
            )
            sys.exit(1)
        return p.resolve()

    # if "GRABDEPS_CONAN_COMMAND" in os.environ:
    #     path = which(os.getenv("GRABDEPS_CONAN_COMMAND"))
    #     if not path:
    #         print(
    #             f"ERROR: GRABDEPS_CONAN_COMMAND was set to: '{os.getenv('GRABDEPS_CONAN_COMMAND')}' but I couldn't find it."
    #         )
    #         sys.exit(1)
    #     path = Path(path).resolve()
    # elif using_reqs():
    #     path = which("conan")
    #     if not path:
    #         print(
    #             "ERROR: conan needs to be in path when using requirements.txt in .plex_dev!"
    #         )
    #         sys.exit(1)
    #     path = Path(path).resolve()
    #     check_conan_version(path)
    else:
        raise TypeError()
        # path = cache_pyz()

    return path


def main():
    verbose_display_python()

    toolchain_path = download_toolchain("https://artifacts.plex.tv/clang-plex")

    # Insert our toolchain at the start
    if toolchain_path:
        prepend_env_var("PATH", str(toolchain_path / "bin"))
        CONAN_ENV["PLEX_TOOLCHAIN_PATH"] = str(toolchain_path)
        print("herererererere")

    conan_path = get_conan_path()
    print(">>> ", conan_path)
    # raise TypeError()
    process_env()
    install_conan_config(conan_path)
    conan_main(conan_path)


if __name__ == "__main__":
    main()
