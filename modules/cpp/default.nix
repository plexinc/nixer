self:
{
  imports = [ self.default ];

  perSystem = { lib, config, pkgs, self', inputs', system, ... }:
    let
      utils = pkgs.callPackage ./lib;
      stdenv = utils.mkLibcxxStdenv config.llvmVersion;
    in
    {
      options.llvmVersion = lib.mkOption {
        type = lib.types.str;
        description = ''
          What version of LLVM to use.
        '';
      };

      devShells = {
        default = (pkgs.mkShell.override { inherit stdenv; }) {
          nativeBuildInputs = [
            pkgs.cmake
            pkgs.ninja
          ];

          buildInputs = [
            pkgs.musl
          ];
        };
      };
    };
}
