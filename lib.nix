{ nixpkgs-lib }:
{
  mkFlake = { inputs, nixpkgs, ... }: { systems, imports ? [ ], specialArgs ? { } }:
    let
      lib = nixpkgs-lib.lib;
      final = lib.evalModules {
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
    lib.attrsets.recursiveUpdate final.config.perSystem final.config.generic;
}
