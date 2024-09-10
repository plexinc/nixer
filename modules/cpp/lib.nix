{ pkgs }:
with builtins;
{
  # Returns a `stdenv` set for the latest stable LLVM
  # On Linux it will use musl as libc and on all the
  # platforms it uses llvm infrastructure.
  mkLibcxxStdenv = { llvmVersion }:
    # TODO: use llvmVersion to expose other versions of
    # llvm as well
    if pkgs.stdenv.hostPlatform.isLinux
    then pkgs.pkgsMusl.pkgsLLVM.stdenv
    else pkgs.pkgsLLVM.stdenv;
}
