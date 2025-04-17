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
          (withSystem "x86_64-linux")
          (withSystem "aarch64-darwin")
        ];

        imports = [
          ./hello.nix
          ./end-user.nix
        ];
      };
}
