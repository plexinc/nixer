from grabdeps.yml_utils import (
  get_tarball_name,
  get_deps_buildinfo_path,
  parse_config_spec,
  get_configs_for_dep,
  get_sha,
  remap_configs,
  filter_configs,
)


def test_default_name_only_config():
  assert get_tarball_name({}, {"config": "blep"}) == "blep"


def test_name_uses_scheme():
  assert (
    get_tarball_name({"scheme": "boop-{config}"}, {"config": "blep"}) == "boop-blep"
  )


def test_name_uses_variant():
  assert (
    get_tarball_name(
      {"scheme": "{variant}-{config}.tar.zst"},
      {"config": "blep", "variant": "beep"},
    )
    == "beep-blep.tar.zst"
  )


def test_buildinfo_path():
  from pathlib import Path

  entry = {"plex-desktop": {"sha": "beep"}}
  context = {"config": "x86_64-apple-darwin-macos", "variant": "desktop"}
  expected = Path("plex-desktop") / "x86_64-apple-darwin-macos" / "plex-buildinfo.cmake"
  assert get_deps_buildinfo_path("plex-desktop", entry, context) == expected


def test_cfg_specs_parsing():
  parsed = parse_config_spec(["foo"])
  assert "*" in parsed
  assert parsed["*"] == ["foo"]

  parsed = parse_config_spec(["foo", "*:bar"])
  assert "*" in parsed
  assert parsed["*"] == ["foo", "bar"]

  parsed = parse_config_spec(["dep1:foo", "dep2:bar"])
  assert "*" not in parsed
  assert "dep1" in parsed
  assert "dep2" in parsed
  assert parsed["dep1"] == ["foo"]
  assert parsed["dep2"] == ["bar"]

  parsed = parse_config_spec(["dep1:foo", "dep2:bar", "quaz", "*:beep"])
  assert "*" in parsed
  assert "dep1" in parsed
  assert "dep2" in parsed
  assert parsed["*"] == ["quaz", "beep"]
  assert parsed["dep1"] == ["foo"]
  assert parsed["dep2"] == ["bar"]


def test_config_selection_for_dep():
  cfgs = {"*": ["foo"]}
  assert get_configs_for_dep("bar", cfgs) == ["foo"]

  cfgs = {"*": ["foo"], "baz": ["bazconf"]}
  assert get_configs_for_dep("bar", cfgs) == ["foo"]
  assert get_configs_for_dep("baz", cfgs) == ["bazconf"]

  cfgs = {}
  assert get_configs_for_dep("nonexistent", cfgs) == []


def test_sha_is_stripped():
  entry = {"sha": "foobar"}
  assert get_sha(entry) == "foobar"

  entry = {"sha": " foobar        "}
  assert get_sha(entry) == "foobar"


def test_remap_configs():
  entry = {"config-map": {"foo": "bar"}}
  assert remap_configs(entry, ["foo", "noremap"]) == ["bar", "noremap"]


def test_filter_configs():
  entry = {"config-exclude": ["variant/config", "config2"]}

  assert filter_configs(entry, ["config", "hello", "config2"], "variant") == ["hello"]
