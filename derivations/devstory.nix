{ buildPythonPackage
, click
, colorama
, yaspin
, appdirs
, requests
, tqdm
, redbaron
, asciitree
, beard
, grabdeps
, packaging
, setuptools
, importlib-metadata
}:
buildPythonPackage rec{
  name = "devstory";
  version = "10.0.0";

  VERSION = version;

  src = ../tools/devstory;

  propagatedBuildInputs = [
    click
    colorama
    yaspin
    appdirs
    requests
    tqdm
    redbaron
    asciitree
    beard
    grabdeps
    packaging
    setuptools
    importlib-metadata
  ];

  doUnpack = false;
  dontUseSetuptoolsCheck = true;
}
