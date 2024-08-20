# Versioning is handled by Nix, don't worry about it.
import os
from setuptools import setup
from packaging.version import Version


def branch_formatter(branch):
    return branch.replace("/", "")


version_string = os.environ.get("VERSION", "0.0.0.dev0")
version = Version(version_string)

setup(
    long_description="grab yo deps but longer",
    name="grabdeps",
    version=str(version),
    description="grab yo deps",
    python_requires="==3.*,>=3.6.0",
    packages=[
        "grabdeps",
        "grabdeps.resources",
        "grabdeps.resources.conan_config",
        "grabdeps.tcutils",
        "grabdeps.tcutils.commands",
    ],
    include_package_data=True,
    package_data={
        "grabdeps.resources.conan_config": ["*"],
    },
    install_requires=[
        "packaging==20.*,>=20.4.0",
        "poyo==0.5.0",
        "importlib_metadata",
    ],
    entry_points={
        "console_scripts": [
            "gd=grabdeps.main:main",
            "gd2=grabdeps.main2:main",
            "pconan=grabdeps.conan_wrapper:main",
            "plexec=grabdeps.plexexec:main",
            "fetch-plex-toolchain=grabdeps.fetch_toolchain:main",
            "plex-toolchain=grabdeps.tcutils.plumbing:cli",
        ]
    },
)
