{ lib
, buildPythonPackage
, click
, colorama
, appdirs
, requests
, packaging
, setuptools
, fetchFromGitHub
}:

buildPythonPackage rec{
  name = "beard";
  version = "1.2.0";

  # src = fetchgithub
  #   {
  #     url = "https://lxsameer@github/plexinc/${name}.git";
  #     shallow = true;
  #     ref = "main";
  #     rev = "4c1b95b1cb8a5a673c55fdbc92bf4708b7d0ffca";
  #   };
  # src = plexFetchFromGitHub {
  #   repo = "beard";
  #   rev = "4c1b95b1cb8a5a673c55fdbc92bf4708b7d0ffca";
  # };

  # src = builtins.fetchGit {
  #   url = "https://github.com/plexinc/beard.git";
  #   shallow = true;
  #   rev = "4c1b95b1cb8a5a673c55fdbc92bf4708b7d0ffca";
  #   ref = "main";
  # };

  src = fetchFromGitHub {
    repo = "beard";
    owner = "plexinc";
    rev = "4c1b95b1cb8a5a673c55fdbc92bf4708b7d0ffca";
    hash = lib.fakeHash;
  };

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
