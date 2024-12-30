{ lib, config, nixpkgs, systems, ... }:
with lib;
{
  options =
    let
      perSystemType = mkOptionType {
        name = "perSystemType";
        description = "A function that receives per system arguments and generate flake outputs attrs";
        descriptionClass = "composite";
        check = isFunction;
        merge = (locs: fileValues:
          let
            perSystemObj = lib.fixedPoints.makeExtensible (final: { });
            fns = map (x: x.value) fileValues;
            replaceAttrs = system: attr: obj: (with builtins;
              if hasAttr attr obj
              # Rewrite the attr with system
              then
                removeAttrs obj [ attr ] // { ${attr}.${system} = obj.${attr}; }
              else obj);

            reducer = fn: system: acc:
              let
                obj = acc.extend (final: prev:
                  # This is the actual call to `perSystem` functions
                  fn {
                    inherit final prev system;
                    pkgs = import nixpkgs {
                      inherit system;
                      inherit (config) overlays;
                    };
                  });
              in
              foldr (replaceAttrs system) obj config.attributes;
            callFn = fn: accObj: foldr (reducer fn) accObj systems;
          in
          foldr callFn perSystemObj fns);
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
        ];
      };
      perSystem = mkOption {
        type = perSystemType;
        description = "Per system flake configuration.";
        default = _: { };
      };

      generic = mkOption {
        type = types.lazyAttrsOf types.unspecified;
        description = "Any system agnostic configuration to be merged with the output";
        example = lib.literalExpression or lib.literalExample ''
          generic = {
            foo = bar;
          };
        '';
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
