# This file exists so we can avoid depending on pkg_resources, which is technically an external
# dependency (it's also a lot faster this way)

DEPS_YAML_VERSION = "1.4"


def get_grabdeps_version():
  from importlib_metadata import version, PackageNotFoundError

  try:
    return version("grabdeps")
  except PackageNotFoundError:
    return "unknown"


def get_deps_yaml_version():
  return DEPS_YAML_VERSION


def is_yaml_version_supported(version_in_config, version_understood):
  if isinstance(version_in_config, float):
    version_in_config = str(version_in_config)

  from packaging.version import parse

  version_understood = parse(version_understood)
  version_in_config = parse(version_in_config)
  if version_understood.major != version_in_config.major:
    # A breaking change
    return False
  if version_understood.minor >= version_in_config.minor:
    # Minor version bumps signify compatible expansions, i.e. we can safely parse
    # a config that is written with a lower minor version in mind.
    return True

  # If we are here, that means the minor version we understand is _lower_ than
  # what the config file requires, i.e. we won't be able to understand parts of it.
  return False


def check_yaml_version(yaml_data):
  return ("!version" in yaml_data) and is_yaml_version_supported(
    yaml_data["!version"], DEPS_YAML_VERSION
  )
