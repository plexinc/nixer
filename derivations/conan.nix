{ lib
, stdenv
, fetchurl
, jinja2
, buildPythonPackage
, pyjwt
, pyyaml
, bottle
, colorama
, deprecation
, distro
, fasteners
, future
, node-semver
, patch-ng
, pluginbase
, pygments
, python-dateutil
, requests
, six
, tqdm
, urllib3
, setuptools
, ipython
, pip
, virtualenvwrapper
, wheel
,
}:

buildPythonPackage rec{
  name = "plex-conan";
  version = "1.25.2";
  src = fetchurl {
    url = "https://files.pythonhosted.org/packages/2b/63/18c12ffbf20e0f30ecaad6fc4ccfc480973d505210c8c74ad192789597d6/conan-1.25.2.tar.gz";
    hash = "sha256-BEPa9n5W+SE8t4qj8i9+qQufVJc0qry/s9Qvb6p4Y/0=";
  };

  format = "setuptools";

  propagatedBuildInputs = [
    jinja2
    pyjwt
    pyyaml
    bottle
    colorama
    deprecation
    fasteners
    future
    node-semver
    patch-ng
    pluginbase
    pygments
    python-dateutil
    requests
    six
    tqdm
    urllib3
  ] ++ lib.optional stdenv.hostPlatform.isLinux [
    distro
  ];

  nativeBuildInputs = [
    # pythonRelaxDepsHook
    setuptools
    pip
    virtualenvwrapper
    wheel
  ];

  doCheck = false;
  dontUseSetuptoolsCheck = true;
}
