import re

from glob import iglob
from pathlib import Path
from collections import defaultdict


class Profile:
  # pylint: disable=too-many-instance-attributes
  def __init__(self, name):
    self.name = Path(name).name
    self.path = Path(name)
    self.lines = open(name).readlines()
    self.data = self._load_data()
    self.settings = self.data.get("settings", None)
    settings = self.settings
    if settings:
      self.os = settings.get("os", None)
      self.arch = settings.get("arch", None)
      self.compiler = settings.get("compiler", None)
      self.build_type = settings.get("build_type", None)
      if "compiler.libcxx" in settings:
        self.libstdcpp = settings["compiler.libcxx"]
      else:
        self.libstdcpp = "dinkumware"

  def _load_data(self):
    profile_data = defaultdict(dict)
    section_rgx = re.compile(r"\[(?P<name>[\w\-]+)\]")
    include_rgx = re.compile(r"include\((?P<filename>[\w\-\.]+)\)")
    included_profiles = []
    section = "__variables__"
    for line in (k.strip() for k in self.lines):
      if not line:
        continue
      match = include_rgx.match(line)
      if match:
        # in order to extend variables that come from includes, we apply the included
        # profiles right away
        included_profile = Profile(str(self.path.parent / match.group("filename")))
        included_profiles.append(included_profile)
        for inc_section in included_profile.data:
          for key, value in included_profile.data[inc_section].items():
            profile_data[inc_section][key] = value
        continue
      match = section_rgx.match(line)
      if match:
        section = match.group("name")
        continue
      if section:
        key, _, value = line.partition("=")
        for match in re.finditer(r"\$(\w+)", value):
          var_name = match.group(1)
          value = value.replace(f"${var_name}", profile_data["__variables__"][var_name])
        profile_data[section.strip()][key.strip()] = value

    return profile_data

  @property
  def env(self):
    return self.data["env"]

  def __repr__(self):
    return "<Profile {0}>".format(self.name)

  def __str__(self):
    return self.name

  def __lt__(self, other):
    return self.name < other.name


def load_profiles():
  from devstory.common import get_profiles_dir

  return (Profile(p) for p in iglob(str(get_profiles_dir()) + "/plex-*"))


def load_profile_by_name(name):
  from devstory.common import get_profiles_dir

  return Profile(str(get_profiles_dir() / name))
