from pathlib import Path

from devstory.common import (
  CommandResult,
  get_project_dir,
  get_toolchain_files,
  get_toolchain_path,
)

from devstory.common import DsConfig

DEFAULT_CONFIG = "i686-windows-msvc-Debug-Standard"

TOOLCHAIN_EXCLUDE_PATTERNS = ("cygwin",)


def is_excluded_toolchain(toolchain: Path) -> bool:
  # technically, that bool() is not needed, but it looked very weird because of
  # the `in` part that is also in the for loop.
  return any(bool(pattern in toolchain.name) for pattern in TOOLCHAIN_EXCLUDE_PATTERNS)


def get_configs():
  # we need to use the raw ConfigParser API here, so we grab the underlying object
  # from DsConfig
  plex_dev = DsConfig.load_plex_dev().cfg
  if not plex_dev.has_section("msvc.configs"):
    # default for PMS (without config)
    return {"i686": ["Standard"], "x86_64": ["Nano"]}

  import json

  configs = {}
  for key, value in plex_dev["msvc.configs"].items():
    lst = json.loads(value)
    configs[key] = lst
  return configs


def do_msvc():
  build_types = ("Debug", "RelWithDebInfo")
  configs = get_configs()
  configurations = []

  def get_intellisense(name):
    envs = {
      "i686-windows-msvc.cmake": "windows-msvc-x86",
      "x86_64-windows-msvc.cmake": "windows-msvc-x64",
      "i686-windows-clang.cmake": "windows-clang-x86",
      "x86_64-windows-clang.cmake": "windows-clang-x64",
    }
    return envs[name]

  def get_env(name):
    envs = {
      "i686-windows-msvc.cmake": "msvc_x86_x64",
      "x86_64-windows-msvc.cmake": "msvc_x64_x64",
      "i686-windows-clang.cmake": "clang_cl_x86",
      "x86_64-windows-clang.cmake": "clang_cl_x64",
    }
    return envs[name]

  build_dir = Path.cwd()
  project_dir = get_project_dir()
  out_dir = f"${{projectDir}}\\{str(build_dir.relative_to(project_dir))}"
  plex_dev = DsConfig.load_plex_dev()

  for toolchain in get_toolchain_files():
    if is_excluded_toolchain(toolchain):
      continue

    for buildtype in build_types:
      arch = toolchain.name.split("-")[0]
      for var in configs[arch]:
        configname = f"{toolchain.name.replace('.cmake', '')}-{buildtype}-{var}"
        config = {
          "name": configname,
          "description": f"{toolchain.name} build_type: {buildtype} variant: {var}",
          "generator": "Ninja",
          "configurationType": buildtype,
          "inheritEnvironments": [get_env(toolchain.name)],
          "intelliSenseMode": get_intellisense(toolchain.name),
          "buildRoot": f"{out_dir}\\${{name}}",
          "installRoot": f"{out_dir}\\install\\${{name}}",
          "cmakeToolchain": str(toolchain.resolve()),
          "variables": [
            {
              "name": plex_dev.load_setting(
                "project", "variant_key", "PLEX_MEDIA_SERVER_VARIATION"
              ),
              "value": var,
              "type": "STRING",
            }
          ],
        }
        if "clang" in configname:
          config["variables"].extend(
            [
              {
                "name": "CMAKE_C_COMPILER",
                "value": str(get_toolchain_path() / "bin" / "clang-cl.exe"),
                "type": "FILEPATH",
              },
              {
                "name": "CMAKE_CXX_COMPILER",
                "value": str(get_toolchain_path() / "bin" / "clang-cl.exe"),
                "type": "FILEPATH",
              },
            ]
          )
        configurations.append(config)

  environments = [{"GRABDEPS_DISABLE_PROGRESSBAR": "1"}]

  cmake_settings = {"configurations": configurations, "environments": environments}

  cmake_settings_path = get_project_dir() / "CMakeSettings.json"
  with open(cmake_settings_path, "w") as settingsfp:
    import json

    json.dump(cmake_settings, settingsfp, indent=2)

  vs_dir = Path(get_project_dir() / ".vs")
  vs_dir.mkdir(exist_ok=True)

  default_config = plex_dev.load_setting("msvc", "default_config", DEFAULT_CONFIG)

  if not (vs_dir / "ProjectSettings.json").is_dir():
    with open(vs_dir / "ProjectSettings.json", "w") as psfp:
      json.dump({"CurrentProjectSetting": default_config}, psfp, indent=2)

  return CommandResult.Success
