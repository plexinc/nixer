# SPDX-FileCopyrightText: 2025 Plex Inc <info@plex.tv>
#
# SPDX-License-Identifier: MIT

{
  description = "An alternative to flake-parts";

  inputs = {
    #nixpkgs-lib.url = "https://github.com/NixOS/nixpkgs/archive/0673e7961019225a7346a24cc47be7265b4700d9.tar.gz";
    privateNixPkgs.url = "github:nixOS/nixpkgs/nixos-unstable";
  };

  outputs = { privateNixPkgs, ... }:
    let
      # system here is used to import nixpkgs for a private use only
      # we use nixpkgs to generate the option docs. This is NOT the
      # same as whan users get.
      system = "x86_64-linux";
      privatePkgs = import privateNixPkgs {
        inherit system;
      };
      lib = import ./lib.nix {
        nixpkgs-lib = privatePkgs.lib;
      };
    in
    {
      inherit (lib) mkFlake;

      # Nope, we're not dogfooding our own flake file.
      packages.${system}.default = privatePkgs.callPackage lib.docs { };
    };
}
