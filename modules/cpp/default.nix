self:
{
  imports = [ self.default ];


  perSystem = { lib, config, pkgs, self', inputs', system, ... }:
    let
      utils = pkgs.callPackage ./lib.nix { };

      targetPkgs = utils.targetPkgs { inherit (config) llvmVersion; };

      # while we can do targetPkgs.stdenv here, its better to call
      # a function to future proof it.
      stdenv = utils.mkLibcxxStdenv { inherit (config) llvmVersion; };
    in
    {
      options.llvmVersion = lib.mkOption {
        type = lib.types.str;
        description = ''
          What version of LLVM to use.
        '';
      };
      config = {
        packages.cppStdenv = stdenv;

        devShells = {
          # Then reason we do an override on the default pkgs.mkShell
          # instead of using targetPkgs.mkShell, is to avoid un-necessary
          # builds. `pkgs` is glibc based on linux. By using it. We will
          # use packages that run on glibc for the dev environment such
          # as cmake or ninja that don't interact with our development
          # via libc. This way we can hit the public cache and be much
          # faster.
          cpp = (pkgs.mkShell.override { inherit stdenv; }) {
            nativeBuildInputs = [
              pkgs.cmake
              pkgs.ninja
            ];

            buildInputs = [
            ];
          };
        };
      };
    };
}
