{ lib
, buildPythonPackage
, click
, colorama
, appdirs
, requests
, packaging
, setuptools
}:

buildPythonPackage rec{
  name = "beard";
  version = "1.2.0";

  src = ../tools/beard;

  propagatedBuildInputs = [
    click
    colorama
    appdirs
    requests
    packaging
    setuptools
  ];
  doUnpack = false;
  dontUseSetuptoolsCheck = true;
}
