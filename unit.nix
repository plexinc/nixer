# SPDX-FileCopyrightText: 2025 Plex Inc <info@plex.tv>
#
# SPDX-License-Identifier: MIT

{ lib, config, nixpkgs, systems, ... }:
with lib;
{
  options =
    let
      update = lib.attrsets.recursiveUpdate;
      perSystemType = mkOptionType {
        name = "perSystemType";
        description = "A function that receives per system arguments and generate flake outputs attrs";
        descriptionClass = "composite";
        check = isFunction;
        merge = locs: fileValues: lib.fixedPoints.fix (self:
          let
            fns = map (x: x.value) fileValues;
            vv = s:
              if builtins.hasAttr "devShells" s
              then s.devShells
              else
                { };
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

            reducer = fn: system: state:
              let
                obj = update state
                  (fn
                    {
                      inherit self system;
                      pkgs = import nixpkgs {
                        inherit system;
                        inherit (config) overlays;
                      };
                    });
              in
              obj;
            callFn = fn: state: foldr (reducer fn) state systems;
            orignalMap = foldr callFn { } fns;
            systemReplacer = system: state: update state (foldr
              (replaceAttrs system)
              orignalMap
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

      overlays = mkOption {
        type = types.listOf (types.functionTo
          (types.functionTo (types.lazyAttrsOf types.unspecified)));

        description = "Overlays to use with nixpkgs";
        example = lib.literalExpression or lib.literalExample ''
          overlays = [(final: prev: {
              foo = prev....;
            };
          )];
        '';
        default = [ (final: prev: { }) ];
      };

      nixPkgsConfig = mkOption {
        type = types.lazyAttrsOf types.unspecified;
        description = "An attrset to be passed to nixpkgs as config.";
        default = { };
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
      #_module.args. = pkgs;
      # We want modules to define arbitrary attributes and don't restrict
      # them for now
      _module.check = false;
    };
}
