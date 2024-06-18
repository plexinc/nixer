{
  description = "Nixer is a set of utilities to make it easier to use Nix at Plex";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixpkgs-conan.url = "github:NixOS/nixpkgs/e912fb83d2155a393e7146da98cda0e455a80fb6";
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixdoc.url = "github:nix-community/nixdoc";
  };

  outputs = { self, nixpkgs, flake-parts, ... }@inputs:
    flake-parts.lib.mkFlake
      {
        inherit inputs;
      }
      (
        let
          plexOverlay = import ./overlays {
            inherit inputs;
          };

          systems = [
            "aarch64-darwin"
            "x86_64-linux"
          ];

        in

        {
          inherit systems;

          flake = {
            overlays.default = plexOverlay;
            inherit systems;
          };


          perSystem = { config, self', inputs', pkgs, system, ... }:
            let
              mkPkgSet = params: (import nixpkgs
                {
                  inherit system;
                  overlays = [ plexOverlay ];
                } // params
              );

              py = pkgs.python38.withPackages (p: with p;[
                plex-conan
                grabdeps
                devstory
                beard
              ]);

              imageBuilder = p: p.dockerTools.buildImage {
                name = "plex/python";
                # architecture = "arm64";
                # This will break reproducable image building
                # created = "now";
                config = {
                  #Cmd = [ "${pkgs.pkgsLinux.bash}/bin/bash" ];
                  WorkingDir = "/app";
                  Volumes = { "/app" = { }; };
                };

                copyToRoot = p.buildEnv {
                  name = "image-root";
                  pathsToLink = [ "/bin" ];
                  paths = [ p.bash py p.busybox p.file ];
                };
                config.Entrypoint = [ "${p.bash}/bin/bash" ];

              };
            in
            {
              _module.args.pkgs = mkPkgSet { };


              devShells.default = pkgs.mkShell (
                {
                  nativeBuildInputs = [
                    py
                  ];
                }
              );

              packages = {
                python38 = py;
                grabdeps = pkgs.python38.pkgs.grabdeps;
                pyImage = imageBuilder pkgs;
              };
            };
        }
      );
}
