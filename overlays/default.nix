{ inputs }:
final: prev:
let
  fetchers = prev.callPackage ../lib/fetchers.nix;
  pylib = prev.callPackage ../lib/python.nix { };
  conanSet = (import inputs.nixpkgs-conan { inherit (prev.hostPlatform) system; });

  packageOverrides = pfinal: pprev: (with pylib;
    rec {
      distro = overrideViaPypi pprev.distro {
        version = "1.1.0";
        sha256 = "722054925f339a39ca411a8c7079f390a41d42c422697bedf228f1a9c46ac1ee";
      };
      deprecation = overrideViaPypi pprev.deprecation {
        version = "2.0.7";
        sha256 = "c0392f676a6146f0238db5744d73e786a43510d54033f80994ef2f4c9df192ed";
      };
      pluginbase = overrideViaPypi pprev.pluginbase {
        version = "0.7.0";
        sha256 = "c0abe3218b86533cca287e7057a37481883c07acef7814b70583406938214cc8";
      };
      six = overrideViaPypi pprev.six {
        version = "1.14.0";
        sha256 = "236bdbdce46e6e6a3d61a337c0f8b763ca1e8717c03b369e87a7ec7ce1319c0a";
      };
      node-semver = overrideViaPypi pprev.node-semver {
        version = "0.6.1";
        sha256 = "4016f7c1071b0493f18db69ea02d3763e98a633606d7c7beca811e53b5ac66b7";
      };
      importlib-metadata = overrideViaPypi pprev.importlib-metadata {
        version = "4.8.3";
        sha256 = "766abffff765960fcc18003801f7044eb6755ffae4521c8e8ce8e83b9c9b0668";
        pname = "importlib_metadata";
      };

      yaspin = pprev.buildPythonPackage rec {
        pname = "yaspin";
        version = "0.18.0";
        src = prev.fetchurl {
          url = "https://files.pythonhosted.org/packages/be/dc/1170a3bff5939990118af79c28d55aa25b2aa94bde1856276f9a2babe70c/yaspin-0.18.0-py2.py3-none-any.whl";
          sha256 = "1p9avajwlcwjq1kvi9a23jqzy0ncb9w0px9daad8i2vycafs2yyk";
        };
        format = "wheel";
        doCheck = false;
        buildInputs = [ ];
        checkInputs = [ ];
        nativeBuildInputs = [ ];
        propagatedBuildInputs = [ ];
      };

      redbaron = pprev.buildPythonPackage rec {
        pname = "redbaron";
        version = "0.8";
        src = prev.fetchurl {
          url = "https://files.pythonhosted.org/packages/18/9d/02a7fab9c51f073263045c2af26bd972fb943806e4ba907de949d20632ca/redbaron-0.8-py2.py3-none-any.whl";
          sha256 = "1mnmgxbwy0cf2wdchy4an9321cvc5hbqcwmgp1ni0hp3k9bqlz17";
        };
        format = "wheel";
        doCheck = false;
        buildInputs = [ ];
        checkInputs = [ ];
        nativeBuildInputs = [ ];
        propagatedBuildInputs = [
          pfinal."baron"
        ];
      };

      plex-conan = pprev.callPackage ../derivations/conan.nix { };
      grabdeps = pprev.callPackage ../derivations/grabdeps.nix { };
      beard = pprev.callPackage ../derivations/beard.nix { };
      devstory = pprev.callPackage ../derivations/devstory.nix {
        inherit (pfinal) grabdeps beard;

      };
    });

  python37 = conanSet.python37.override { inherit packageOverrides; self = python37; };
  python38 = conanSet.python38.override { inherit packageOverrides; self = python38; };
in
{
  inherit (fetchers) plexFetchFromGitHub;
  inherit (pylib) buildPythonPackage overrideViaPypi;
  inherit python37 python38;
}
