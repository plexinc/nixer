{
  description = "Nixer is a set of utilities to make it easier to use Nix at Plex";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixpkgs-conan.url = "github:NixOS/nixpkgs/e912fb83d2155a393e7146da98cda0e455a80fb6";
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixdoc.url = "github:nix-community/nixdoc";
  };

  outputs = { self, nixpkgs, flake-parts, ... }@inputs:
    flake-parts.lib.mkFlake
      {
        inherit inputs;
      }
      ({ lib, withSystem, flake-parts-lib, ... }:

        let
          inherit (flake-parts-lib) importApply;

          systems = [
            "aarch64-darwin"
            "x86_64-linux"
          ];

          flakeModules = lib.fix (import ./modules {
            inherit inputs importApply withSystem flake-parts-lib lib;
          });

        in

        {
          imports = [
            ./tests
            flakeModules.cpp
          ];

          inherit systems;

          flake = {
            inherit flakeModules systems;
          };

          perSystem = { pkgs, lib, ... }: { };
        });
}
