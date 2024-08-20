from grabdeps.version import is_yaml_version_supported


def test_equal_versions_work():
  assert (
    is_yaml_version_supported(version_in_config="1.0", version_understood="1.0") == True
  )


def test_major_version_breaks():
  assert (
    is_yaml_version_supported(version_in_config="1.0", version_understood="2.0")
    == False
  )


def test_bigger_minor_version_understood_works():
  assert (
    is_yaml_version_supported(version_in_config="1.0", version_understood="1.3") == True
  )


def test_lower_minor_version_understood_breaks():
  assert (
    is_yaml_version_supported(version_in_config="1.5", version_understood="1.3")
    == False
  )


def test_float_version_from_config_accepted():
  assert (
    is_yaml_version_supported(version_in_config=1.0, version_understood="1.0") == True
  )
