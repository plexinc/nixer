{ lib, python3Packages, plexFetchFromGitHub, fetchPypi }:
{
  /*
  * Builds a `setup.py` base python package.
  * `name`: Then name of the repo
  * `version`: What version we are building
  * `rev`: What commit
  * `ref`: What git ref (default `main`)
  * Any other parameters that get passed to this function will be passed
  * and override the deafult value of`pkgs.python3Packages.buildPythonApplication`.
  */
  buildPythonPackage = { name, version, rev, ref ? "main", ... }@params:
    python3Packages.buildPythonApplication
      (with python3Packages;
      {
        inherit name version;

        src = plexFetchFromGitHub {
          inherit name ref rev;
        };

        nativeBuildInputs = [
          python3
          pip
        ];
        doUnpack = false;
        dontUseSetuptoolsCheck = true;
      } // params);

  overrideViaPypi = pkg: { version, sha256, pname ? pkg.pname }: pkg.overrideAttrs (old: {
    inherit version;
    src = fetchPypi {
      inherit pname;
      inherit version sha256;
    };
  });
}
