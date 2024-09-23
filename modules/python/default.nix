self:
{
  imports = [ self.default ];
  perSystem = { pkgs, lib, system, ... }:
    let
      plexOverlay = import ../../overlays { inherit (self) inputs; };
      pkgs' = (import self.inputs.nixpkgs {
        inherit system;
        overlays = [ plexOverlay ];
      });

      py = pkgs'.python38.withPackages (p: with p;[
        plex-conan
        grabdeps
        devstory
        beard
      ]);
    in
    {
      config = {
        devShells.python = pkgs.mkShell (
          {
            nativeBuildInputs = [
              py
            ];
          }
        );

        packages = {
          python38 = py;
          grabdeps = pkgs'.python38.pkgs.grabdeps;
        };
      };
    };
}
