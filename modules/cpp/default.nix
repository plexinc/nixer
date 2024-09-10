self:
{
  imports = [ self.default ];


  perSystem = { lib, config, pkgs, self', inputs', system, ... }:
    let
      utils = pkgs.callPackage ./lib.nix { };
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
