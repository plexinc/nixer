{ python3Packages, beard, grabdeps }:
with python3Packages;
buildPythonApplication rec{
  name = "devstory";
  version = "10.0.0";

  env.VERSION = version;

  src = builtins.fetchGit
    {
      url = "ssh://git@github.com/plexinc/${name}.git";
      shallow = true;
      ref = "v10";
      rev = "f38fc0862db9a606e54e3c2497a7d670763acfa4";
    };

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
