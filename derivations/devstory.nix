{ buildPythonApplication
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
buildPythonApplication rec{
  name = "devstory";
  version = "10.0.0";

  env.VERSION = version;

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
