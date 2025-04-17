# SPDX-FileCopyrightText: 2025 Plex Inc <info@plex.tv>
#
# SPDX-License-Identifier: MIT

{ lib, config, nixpkgs, systems, ... }:
with lib;
{
  options =
    let
      update = lib.attrsets.recursiveUpdate;
      # The whole point of this type is to first:
      # verify the `perSystem` function and second,
      # Create a package set for each provided system
      # and call the `perSystem` function with that pkgs
      # and finally merged them together to form the output.
      # This type rewrites some of the attributes that are
      # provided via `attributes` module option, with
      # respect to the `buildPlatform.system`.
      # For example: `packages.default` will be rewritten to
      # `packages.${system}.default`. Here, system refers to the
      # buildPlatform's system.
      perSystemType = mkOptionType {
        name = "perSystemType";
        description = "A function that receives per system arguments and generate flake outputs attrs";
        descriptionClass = "composite";
        check = isFunction;
        merge = locs: fileValues: lib.fixedPoints.fix (self:
          let
            makePkgsFor = system:
              import nixpkgs ({
                inherit (config) overlays;
              } // system);

            fns = map (x: x.value) fileValues;
            replaceAttrs = system: attr: obj: (with builtins;
              if hasAttr
                attr
                obj
              # Rewrite the attr with system
              then
                update (removeAttrs obj [ attr ])
                  {
                    ${attr}.${system} = obj.${attr};
                  }
              else obj);

            reducer = pkgs: fn: system: state: update state (fn {
              inherit self pkgs;
              system = pkgs.buildPlatform.system;
            });

            callFn = pkgs: fn: state: foldr (reducer pkgs fn) state systems;
            orignalMap = pkgs: foldr (callFn pkgs) { } fns;
            systemReplacer = system: state:
              let
                pkgs = makePkgsFor system;
              in
              update state (foldr
                (replaceAttrs pkgs.hostPlatform.system)
                (orignalMap pkgs)
                config.attributes);
          in
          foldr systemReplacer { } systems);
      };
    in
    {
      packages = mkOption {
        type = types.lazyAttrsOf types.unspecified;
        description = "Just for testing purposes";
        default = { };
      };


      overlays =
        let
          singleOverlayType = types.functionTo (types.functionTo (types.lazyAttrsOf types.unspecified));
          listOfOverlays = types.listOf singleOverlayType;
        in

        mkOption {
          type = listOfOverlays;

          description = ''Overlays to use with nixpkgs. It's a list of overlay
            functions to apply to **ALL** the package sets. Thus the module
            author should make the overlay build/host/target Platform aware.
          '';

          example = lib.literalExpression or lib.literalExample ''
            overlays = [(final: prev: {
                foo = prev....;
              };
            )];
          '';
          default = [ ];
        };

      attributes = mkOption {
        type = types.listOf (types.str);
        description = "List of attributes to make system aware via nixer";
        default = [
          "packages"
          "apps"
          "devShells"
          "checks"
        ];
      };

      perSystem = mkOption {
        type = perSystemType;
        description = "Per system flake configuration.";
        default = _: { };
      };

      helpers = mkOption {
        type = types.attrsOf types.unspecified;
        description = ''
          An attrset of helper functions or data structures that
          modules can use to expose to user
        '';

        default = { };
      };
      generic = mkOption {
        type = types.attrsOf types.unspecified;
        description = "Any system agnostic configuration to be merged with the output";
        example = lib.literalExpression or lib.literalExample ''
          generic = {
            foo = bar;
          };
        '';
        default = { };
      };
    };
  config =
    {
      _module.check = false;
    };
}
