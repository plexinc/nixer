{
  perSystem = { pkgs, system, lib, ... }:
    let
      llvmVersion = "18";
      cppLib = pkgs.callPackage ../../modules/cpp/lib.nix { inherit pkgs; };
      stdenv = cppLib.mkLibcxxStdenv { inherit llvmVersion; };
      mkTest = pname: (import ../mkTest.nix {
        inherit pname stdenv;
      });
      isLinux = pkgs.stdenv.hostPlatform.isLinux;
    in
    {
      checks = {
        cppPlain = mkTest "test-compiling-a-simple-program" {
          src = if isLinux then ./plain-musl else ./plain;

          nativeBuildInputs =
            (with pkgs; [ cmake ninja ]);

          cmakeFlags = [ ];
          ninjaFlags = [ "-v" ];
          checkPhase =
            if isLinux
            then ''
              ${pkgs.pax-utils}/bin/lddtree main
              ldd main|grep 'libc++' && echo "Success: Linked against libc++" || (echo "Error: Executable isn't link against libc++" && exit 1)
              ldd main|grep 'libgcc' && echo "Error: Linked against libgcc???" && exit 1 || echo "Success: No libgcc"
              ldd main|grep musl && echo "Success: Linked against Musl" || (echo "Error: Executable isn't link against Musl" && exit 1)
              ./main
            ''
            else ''
              otool -L main|grep 'libc++' && echo "Success: Linked against libc++" || (echo "Error: Executable isn't link against libc++" && exit 1)
              otool -L main|grep 'libgcc' && echo "Error: Linked against libgcc???" && exit 1 || echo "Success: No libgcc"
              ./main
            '';
        };
      };
    };
}
