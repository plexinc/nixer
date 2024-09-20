# This argument is the same if what we provide
# in the main flake for all the modules
localFlake:
# Target flake, runtime
self:
let
  self' = self // localFlake;

  lib = localFlake.lib;
  inherit (self'.flake-parts-lib)
    mkPerSystemOption;

  inherit (self'.lib) types mkOption;

  overlays = mkOption {
    type = types.types.lazyAttrsOf (types.uniq (types.functionTo (types.functionTo (types.lazyAttrsOf types.unspecified))));
    # This eta expansion exists for the sole purpose of making nix flake check happy.
    apply = lib.mapAttrs (_k: f: final: prev: f final prev);
    default = { };
    example = lib.literalExpression or lib.literalExample ''
      {
        default = final: prev: {};
      }
    '';
    description = ''
      An attribute set of [overlays](https://nixos.org/manual/nixpkgs/stable/#chap-overlays).

      Note that the overlays themselves are not mergeable. While overlays
      can be composed, the order of composition is significant, but the
      module system does not guarantee sufficiently deterministic
      definition ordering, across versions and when changing `imports`.
    '';
  };
  commonSubmodule = types.submodule {
    options = {
      inherit overlays;
      name = mkOption {
        type = types.str;
        description = "The main name of the project";
      };

      src = mkOption {
        type = types.path;
        description = "Path to the current project";
      };

      llvmVersion = lib.mkOption {
        type = lib.types.str;
        default = "18";
        description = ''
          What version of LLVM to use.
        '';
      };
    };
  };

in
{
  default = {
    options = {
      perSystem = mkPerSystemOption
        ({ config, self', inputs', pkgs, system, ... }: {
          options = {
            nixer = mkOption {
              type = commonSubmodule;
              description = "Common nixer configuration options";
            };
          };
          config = {
            _module.args.pkgs = import localFlake.inputs.nixpkgs {
              inherit system;
              overlays = [
                (final: prev:
                  let
                    llvm = "llvmPackages_${config.nixer.llvmVersion}";
                    #llvm = "llvmPackages_18";
                  in
                  {
                    llvmPackages = prev.${llvm};
                  })
                #(builtins.attrValues config.nixer.overlays)
              ];
              config = { };
            };
          };
        });
    };
  };
  cpp = localFlake.importApply ./cpp self';
  # treefmt = localFlake.importApply ./common/treefmt.nix self';
  # githooks = localFlake.importApply ./common/githooks.nix self';
}
