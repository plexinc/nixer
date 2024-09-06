{ pkgs }:
with builtins;
{

  # Returns a `stdenv` set for the given `llvmVersion`.
  # On Linux it will use musl as libc and on all the
  # platforms it uses llvm infrastructure.
  mkLibcxxStdenv = llvmVersion:
    let
      llvm = "llvmPackages_${llvmVersion}";
      muslClang = pkgs.pkgsMusl.llvmPackages_18.libcxxStdenv.cc;
      stdenv' = pkgs.${llvm}.libcxxStdenv;
    in
    if pkgs.stdenv.hostPlatform.isLinux
    then pkgs.stdenvAdapters.overrideCC stdenv' muslClang
    else stdenv';
}
