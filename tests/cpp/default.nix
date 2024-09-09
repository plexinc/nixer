{
  perSystem = { pkgs, system, ... }:
    let
      llvmVersion = "18";
      cppLib = pkgs.callPackage ../../modules/cpp/lib.nix { inherit pkgs; };
      stdenv = cppLib.mkLibcxxStdenv llvmVersion;
      mkTest = pname: (import ../mkTest.nix { inherit pname stdenv; });
    in
    {
      checks = {
        cppPlain = mkTest "test-compiling-a-simple-program" {
          src = if pkgs.stdenv.hostPlatform.isLinux then ./plain-musl else ./plain;

          nativeBuildInputs =
            (with pkgs; [ cmake ninja ]);

          cmakeFlags = [ ];
          ninjaFlags = [ "-v" ];

          checkPhase = ''
            ldd main
            ldd main|grep musl && echo "Success: Linked against Musl" || (echo "Error: Executable isn't link against Musl" && exit 1)
            ldd main|grep 'libcxx-${llvmVersion}' && echo "Success: Linked against libc++" || (echo "Error: Executable isn't link against libc++" && exit 1)
            ./main
          '';
        };
      };
    };
}
