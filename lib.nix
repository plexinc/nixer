{ nixpkgs-lib }:
{
  mkFlake = { inputs, nixpkgs, ... }: { systems, imports ? [ ] }:
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
        };
      };
    in
    final.config.perSystem;

}
