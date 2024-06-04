{ inputs }:
final: prev:
let
  fetchers = prev.callPackage ./lib/fetchers.nix;
  pylib = prev.callPackage ./lib/python.nix { };

in
{
  inherit (fetchers) plexFetchFromGitHub;
  inherit (pylib) buildPythonPackage;

  plex-conan = (import inputs.nixpkgs-conan { inherit (prev.hostPlatform) system; }).conan;
  devstory = prev.callPackage ./derivations/devstory.nix { };
  grabdeps = prev.callPackage ./derivations/grabdeps.nix { };
  beard = prev.callPackage ./derivations/beard.nix { };
}
