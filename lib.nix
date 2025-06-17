# SPDX-FileCopyrightText: 2025 Plex Inc <info@plex.tv>
#
# SPDX-License-Identifier: MIT

{ nixpkgs-lib }:
{
  mkFlake = { inputs, nixpkgs, ... }: { systems, imports ? [ ], specialArgs ? { }, ... }:
    let
      final = nixpkgs-lib.evalModules {
        # The unit module is mandatory and the bare min
        # config that is necessary
        modules = [
          ./unit.nix
        ] ++ imports;

        specialArgs = {
          inherit nixpkgs systems;
        } // specialArgs;
      };
    in
    nixpkgs-lib.attrsets.recursiveUpdate final.config.perSystem final.config.generic;

  docs = { lib, runCommand, asciidoctor-with-extensions, nixosOptionsDoc, ... }:
    let
      final = lib.evalModules {
        modules = [
          ./unit.nix
        ];

        specialArgs = { };
      };
      adocs = (nixosOptionsDoc {
        inherit (final) options;
      }).optionsAsciiDoc;
    in
    runCommand "gen-html" { } ''
      mkdir -p $out
      cp -v ${adocs} $out/options.adoc
      cp -v ${./docs/index.adoc} $out/index.adoc
      ls -l $out
      ${asciidoctor-with-extensions}/bin/asciidoctor -a linkcss -a copycss $out/index.adoc -o $out/index.html
    '';
}
