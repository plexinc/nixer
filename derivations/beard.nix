{ buildPythonPackage
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

  src = builtins.fetchGit
    {
      url = "ssh://git@github.com/plexinc/${name}.git";
      shallow = true;
      ref = "main";
      rev = "4c1b95b1cb8a5a673c55fdbc92bf4708b7d0ffca";
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
