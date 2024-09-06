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
  perSystem = { pkgs, ... }: {
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
