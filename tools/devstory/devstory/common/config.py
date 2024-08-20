from configparser import ConfigParser, NoSectionError, NoOptionError
from pathlib import Path
from typing import List

import platform

import appdirs

from devstory import output


class DsConfig:
  def __init__(self, cfg_path=None):
    self.cfg_path = cfg_path or self._default_cfg_path()
    Path(self.cfg_path).parent.mkdir(parents=True, exist_ok=True)

  @staticmethod
  def load_plex_dev():
    from devstory.common import get_project_dir

    return DsConfig(get_project_dir() / ".plex_dev")

  @staticmethod
  def _default_cfg_path():
    return str(Path(appdirs.user_config_dir()) / "devstory.cfg")

  @property
  def cfg(self) -> ConfigParser:
    cfg = ConfigParser()
    if Path(self.cfg_path).exists():
      cfg.read(self.cfg_path)
    return cfg

  def load_setting(self, section, key, default=None):
    cfg = self.cfg
    # Allow platform-specific sections transparently
    section_names = f"{section}.{platform.system().lower()}", section
    for sname in section_names:
      output.trace(f"Trying section name {sname}")
      if sname in cfg.sections():
        if key in cfg[sname]:
          return cfg[sname][key].strip('"')
      else:
        output.trace("  - no such section or key")
    return default

  def has_setting(self, section, key):
    return self.load_setting(section, key, None) is not None

  def load_project_setting_ctx(self, context, key, default=None):
    """This function will try to load a setting from context.stored_flags.
    If the setting is not there, it will fall back to load_setting("project", key)
    """
    stored_flags = context.stored_flags
    if key in stored_flags and stored_flags[key] is not None:
      return stored_flags[key]
    return self.load_setting("project", key, default)

  def load_list_setting(self, section, key, default=None) -> List[str]:
    import json

    value = self.load_setting(section, key)
    if value:
      return json.loads(value)
    return default or []

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
