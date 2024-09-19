{ pkgs }:
with builtins;
rec {
  # Return a package set for the target Platform
  # TODO: Find a better name for this function
  targetPkgs = { llvmVersion }:
    # TODO: use llvmVersion to expose other versions of
    # llvm as well
    if pkgs.stdenv.hostPlatform.isLinux
    then pkgs.pkgsMusl.pkgsLLVM
    else pkgs;

  # Returns a `stdenv` set for the latest stable LLVM
  # On Linux it will use musl as libc and on all the
  # platforms it uses llvm infrastructure.
  mkLibcxxStdenv = params: (targetPkgs params).stdenv;
}
