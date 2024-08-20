import re

from glob import iglob
from pathlib import Path
from collections import defaultdict


class ConanIniParser:
  """
  Parses the conan flavor of ini/txt config files. This includes
  files and conaninfo.txt etc.
  """

  # pylint: disable=too-many-instance-attributes
  def __init__(self, name):
    self.name = Path(name).name
    self.path = Path(name)
    self.lines = open(name).readlines()
    self.data = self._load_data()

  def _load_data(self):
    file_data = defaultdict(dict)
    section_rgx = re.compile(r"\[(?P<name>[\w\-]+)\]")
    include_rgx = re.compile(r"include\((?P<filename>[\w\-\.]+)\)")
    included_files = []
    section = None
    for line in (k.strip() for k in self.lines):
      if not line:
        continue
      match = include_rgx.match(line)
      if match:
        included_files.append(
            Profile(str(self.path.parent / match.group("filename"))))
        continue
      match = section_rgx.match(line)
      if match:
        section = match.group("name")
        continue
      if section:
        key, _, value = line.partition("=")
        file_data[section.strip()][key.strip()] = value

    result = defaultdict(dict)
    # Apply all included files in the order of inclusion, so any later
    # includes overwrite previous values. Finally apply the currently read
    # file values.
    for included_file in included_files:
      for section in included_file.data:
        for key, value in included_file.data[section].items():
          result[section][key] = value
    for section in file_data:
      for key, value in file_data[section].items():
        result[section][key] = value
    return dict(result)

  def __repr__(self):
    return "<ConanIni {0}>".format(self.name)

  def __str__(self):
    return self.name

  def __lt__(self, other):
    return self.name < other.name
