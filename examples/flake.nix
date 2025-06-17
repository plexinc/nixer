{
  description = "Nixer examples";

  inputs =
    {
      nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
      nixer.url = "./..";
    };

  outputs = { self, nixpkgs, nixer, ... }@inputs:
    let
      withSystem = system: { inherit system; };
    in
    nixer.mkFlake { inherit inputs nixpkgs; }
      {
        systems = [
          {
            system = "x86_64-linux";
            crossSystem = lib.systems.examples.raspberryPi;
          }
        ];

        imports = [
          ./hello.nix
          ./end-user.nix
        ];
      };
}
