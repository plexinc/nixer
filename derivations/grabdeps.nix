{ python3Packages, python3, plex-conan }:
with python3Packages;
buildPythonPackage rec{
  name = "grabdeps";
  version = "9.0.0";
  env.VERSION = version;

  src = builtins.fetchGit
    {
      url = "ssh://git@github.com/plexinc/${name}.git";
      shallow = true;
      ref = "v9";
      rev = "50353d26ccf2094e1903df4ee91cdc37a1383599";
    };

  nativeBuildInputs = with python3.pkgs; [
    pythonRelaxDepsHook
  ];

  propagatedBuildInputs = [ setuptools packaging poyo importlib-metadata plex-conan ];
  doUnpack = false;
  dontUseSetuptoolsCheck = true;
}
