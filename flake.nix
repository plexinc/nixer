{
  description = "Nixer is a set of utilities to make it easier to use Nix at Plex";

  # the nixConfig here only affects the flake itself, not the system configuration!
  nixConfig = {
    # override the default substituters aka binary caches
    substituters = [
      "https://cache.nixos.org"
      # nix community's cache server
      "https://nix-community.cachix.org"

      # Our own binary cache
      "s3://cache.plex.bz"

    ];
    trusted-public-keys = [
      "nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs="

      # This is the public key
      "cache.plex.bz:Vdh+jRJPqfHyL3Mq5fHqRVMOoI3Jg6eSXkafBgY2eRU="
    ];
  };

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

          perSystem = { ... }: { };
        });
}
