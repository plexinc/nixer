self:
with builtins;
{
  imports = [ ];

  perSystem = { lib, config, pkgs', self', inputs', system, ... }:
    let

      getBuildEnv = p: (p.env or { }).NIX_LDFLAGS or p.NIX_LDFLAGS or "";

      # Most of these overlays are do to bugs and problems
      # in upstream nixpkgs. But thanks to their design
      # We can fix them using these overlays and contribute
      # them upstream little by little.
      overlays = (final: prev:
        if !prev.stdenv.hostPlatform.isLinux then
          prev
        else {

          p11-kit = prev.p11-kit.overrideAttrs
            (old: { patches = [ ./nix/patches/p11-kit_skip_test.patch ]; });

          cpio = prev.cpio.overrideAttrs (old: {
            nativeBuildInputs = [ final.autoreconfHook ];
            NIX_CFLAGS_COMPILE = "-Wno-implicit-function-declaration";
          });

          libedit = prev.libedit.overrideAttrs (old: {
            # Musl is ISO 10646 compliant but doesn't define __STDC_ISO_10646__ we need to do it ourselves
            NIX_CFLAGS_COMPILE = "-D__STDC_ISO_10646__=201103L";
          });

          elfutils = prev.elfutils.overrideAttrs (old: {
            # libcxx does not have __cxa_demangle
            configureFlags = old.configureFlags ++ [ "--disable-demangler" ];
          });

          ccache = prev.ccache.overrideAttrs (old: {
            nativeBuildInputs = old.nativeBuildInputs ++ [ final.elfutils ];
          });

          # We don't need systemd at all
          util-linux = prev.util-linux.override { systemdSupport = false; };

          # libpam exmaples use glibc. We need to disable them
          linux-pam = prev.linux-pam.overrideAttrs (old: {
            postConfigure = ''
              sed 's/examples//' -i Makefile
            '';
          });

          #=============================================================
          # Since we're using lld-18, and --no-undefined-version is the
          # default in lld-18. We need to explicitly turn it off for
          # these problematic packages untill they fix it upstream.
          libxcrypt = prev.libxcrypt.overrideAttrs (old: {
            env.NIX_LDFLAGS = "${getEnv old} --undefined-version";

            #old.NIX_FLAGS ++ final.lib.optional (prev.stdenv.cc.isClang)
          });

          ncurses = prev.ncurses.overrideAttrs
            (old: { env.NIX_LDFLAGS = "${getEnv old} --undefined-version"; });

          libbsd = prev.libbsd.overrideAttrs (old: {
            env.NIX_LDFLAGS = "${getEnv old} --undefined-version";
            # NIX_LDFLAGS = [ ] ++ final.lib.optional (prev.stdenv.cc.isClang)
            #   [ "--undefined-version" ];
          });

          libxml2 = prev.libxml2.overrideAttrs (old: {
            env.NIX_LDFLAGS = "${getEnv old} --undefined-version";
            propagatedBuildInputs = old.propagatedBuildInputs
              ++ [ final.zlib.static ];
            # NIX_LDFLAGS = [ ] ++ final.lib.optional (prev.stdenv.cc.isClang)
            #   [ "--undefined-version" ];
          });

          # binutils = prev.binutils.overrideAttrs (old: {
          #   env.NIX_LDFLAGS = (getEnv old NIX_LDFLAGS " ") ++ "--undefined-version";
          #   buildInputs = [ final.zlib final.gettext final.zlib.static ];
          # });

        });


      hostPkgs = pkgs';
      targetPkgs =
        if elem system [ "x86_64-linux" "aarch64-linux" ]
        then
          import self.inputs.nixpkgs
            {
              inherit system overlays;
              linker = "lld";
              crossSystem = nixpkgs.lib.systems.examples.musl64 // {
                useLLVM = true;
              };
            }
        else
          import nixpkgs { inherit system overlays; };

      stdenv = targetPkgs.stdenvAdapters.overrideCC targetPkgs.stdenv
        targetPkgs.llvmPackages_18.clangUseLLVM;

      zlib' = targetPkgs.zlib-ng.overrideAttrs (old: {
        cmakeFlags = [
          "-DCMAKE_INSTALL_PREFIX=/"
          "-DBUILD_SHARED_LIBS=OFF"
          "-DINSTALL_UTILS=ON"
          "-DZLIB_COMPAT=ON"
        ];
      });
      # By default llvm adds zlib to `propagatedBuildInputs` which means any
      # package that uses llvm will indirectly depends on zlib. And since
      # by default that zlib is built as a shared lib (since our packageset
      # is not static), We can't statically link to it. So, we just replace
      # that zlib with our override of zlib-ng
      clang' = stdenv.cc.overrideAttrs (old: {
        propagatedBuildInputs = [ stdenv.cc.bintools ]
          ++ [ targetPkgs.zlib.static ];
      });

      llvmPackages = targetPkgs.pkgsLLVM.llvmPackages_18;
      llvm = llvmPackages.llvm.overrideAttrs
        (old: { propagatedBuildInputs = [ targetPkgs.zlib.static ]; });

      # This is the actual stdenv that we need to use anywhere else
      stdenv' =
        targetPkgs.stdenvAdapters.overrideCC targetPkgs.stdenv clang';

      nativeBuildToolsDeps = (with hostPkgs; [ cmake ninja ccache ]);

      staticLibxml2 = targetPkgs.libxml2.override { enableStatic = true; };

      libcxx = llvmPackages.libcxx.override { enableShared = false; };

      buildToolsDeps = (with targetPkgs.pkgsLLVM; [
        llvm
        llvm.dev
        llvmPackages.clang
        llvmPackages.lld
      ]);

      buildDeps = (with targetPkgs.pkgsLLVM; [
        zlib'
        llvm
        llvm.dev
        libcxx
        llvmPackages.compiler-rt
      ]);

      testDeps = (with hostPkgs; [ gtest gmock gbenchmark ]);
    in
    {
      devShells = {
        default = (targetPkgs.mkShell.override { stdenv = stdenv'; }) {
          nativeBuildInputs = nativeBuildToolsDeps ++ buildToolsDeps;
          buildInputs = buildDeps ++ testDeps;
        };
      };
    };
}
