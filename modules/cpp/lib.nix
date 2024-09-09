{ pkgs }:
with builtins;
{

  # Returns a `stdenv` set for the given `llvmVersion`.
  # On Linux it will use musl as libc and on all the
  # platforms it uses llvm infrastructure.
  mkLibcxxStdenv = _:
    if pkgs.stdenv.hostPlatform.isLinux
    then pkgs.pkgsMusl.pkgsLLVM.stdenv
    else pkgs.pkgsLLVM.stdenv;
}
