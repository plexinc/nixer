import os

from setuptools import setup
from packaging.version import Version


def branch_formatter(branch):
  return branch.replace("/", "")

version_string = os.environ.get("VERSION", "0.0.0.dev0")
version = Version(version_string)

setup(
  name="devstory",
  version=str(version),
  packages=[
    "devstory",
    "devstory.commands",
    "devstory.commands.msvc",
    "devstory.commands.clion",
    "devstory.resources",
    "devstory.common",
  ],
  version_config={
    "starting_version": "2",
    "template": "{tag}.{env:BUILD_NUMBER:9999}",
    "dev_template": "{tag}.{env:TSTAMP:{timestamp:%y%m%d%H%M}}.dev{ccount}",
    "dirty_template": "{tag}.{env:TSTAMP:{timestamp:%y%m%d%H%M}}.dev{ccount}+dirty",
    "branch_formatter": branch_formatter,
  },
  package_data={"": ["*.in"], "devstory.resources": ["*"]},
  include_package_data=True,
  license="Internal",
  long_description=open("README.md").read(),
  install_requires=open("requirements.txt").readlines(),
  entry_points={
    "console_scripts": ["ds=devstory.main:main"],
  },
)
