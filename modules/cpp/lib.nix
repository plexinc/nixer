{ pkgs }:
with builtins;
{

  # Returns a `stdenv` set for the given `llvmVersion`.
  # On Linux it will use musl as libc and on all the
  # platforms it uses llvm infrastructure.
  mkLibcxxStdenv = llvmVersion:
    let
      llvm = "llvmPackages_${llvmVersion}";
      # We can uselibcxxStdenv.cc instead;
      muslClang = pkgs.pkgsMusl.llvmPackages_18.clangUseLLVM; # .overrideAttrs (old: {
      #   extraBuildCommands = old.extraBuildCommands + ''
      #     echo "-rtlib=compiler-rt -Wno-unused-command-line-argument" >> $out/nix-support/cc-cflags
      #   '';
      # });
      stdenv' = pkgs.${llvm}.libcxxStdenv;
    in
    if pkgs.stdenv.hostPlatform.isLinux
    then pkgs.stdenvAdapters.overrideCC stdenv' muslClang
    else stdenv';
}
