{
  description = "An alternative to flake-parts";

  # We're using the `lib` tree of nixpkgs
  inputs.nixpkgs-lib.url = "https://github.com/NixOS/nixpkgs/archive/0673e7961019225a7346a24cc47be7265b4700d9.tar.gz";

  outputs = { nixpkgs-lib, ... }@inputs:
    let
      lib = import ./lib.nix {
        inherit nixpkgs-lib;
      };
    in
    { inherit (lib) mkFlake; };
}
