from configparser import ConfigParser, NoSectionError, NoOptionError
from pathlib import Path


class Config(object):
  def __init__(self, cfg_path):
    self.cfg_path = cfg_path

  @property
  def cfg(self):
    cfg = ConfigParser()
    if Path(self.cfg_path).exists():
      cfg.read(self.cfg_path)
    return cfg

  def load_setting(self, section, key):
    cfg = self.cfg
    if section in cfg.sections():
      if key in cfg[section]:
        return cfg[section][key]
    return None

  def load_list_setting(self, section, key):
    import json
    value = self.load_setting(section, key)
    if value:
      return json.loads(value)
    return []

  def save_setting(self, section, key, value):
    cfg = self.cfg
    if section not in cfg:
      cfg.add_section(section)
    cfg[section][key] = value
    with open(self.cfg_path, "w") as configfile:
      cfg.write(configfile)

  def add_to_list(self, section, key, value):
    import json
    entry = self.load_list_setting(section, key)
    entry.append(value)
    self.save_setting(section, key, json.dumps(entry))

  def delete_setting(self, section, key, allow_fail=True):
    cfg = self.cfg
    try:
      cfg.remove_option(section, key)
    except (NoSectionError, NoOptionError):
      if not allow_fail:
        raise
    with open(self.cfg_path, "w") as configfile:
      cfg.write(configfile)
