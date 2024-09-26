{ buildPythonPackage
, writeScript
, plex-conan
, setuptools
, ipython
, pip
, virtualenvwrapper
, wheel
, packaging
, poyo
, importlib-metadata
, certifi
}:

let
  hook = writeScript "setup-hook.sh" ''
    export GRABDEPS_CONAN_COMMAND="${plex-conan}/bin/conan";
    export ARTIFACTORY_USER="00"
    export ARTIFACTORY_PASSWORD="1"
    export CONAN_PASSWORD_TOOLCHAIN="1"
    export CONAN_LOGIN_USERNAME_TOOLCHAIN="1"
    export CONAN_PASSWORD_EXPERIMENTAL="1"
    export CONAN_LOGIN_USERNAME_EXPERIMENTAL="1"
    export CONAN_PASSWORD_TEST="1"
    export CONAN_LOGIN_USERNAME_TEST="1"
    export CONAN_PASSWORD_LLVM="1"
    export CONAN_LOGIN_USERNAME_LLVM="1"
    export CONAN_PASSWORD_MAIN=""
    export CONAN_LOGIN_USERNAME_MAIN="1"
    export CONAN_PASSWORD_NEW="1"
    export CONAN_LOGIN_USERNAME_NEW="1"

  '';
in
buildPythonPackage rec{
  name = "grabdeps";
  version = "9.0.0";
  VERSION = version;
  GRABDEPS_CONAN_COMMAND = "${plex-conan}/bin/conan";

  src = ../tools/grabdeps;

  #setupHook = "${hook}";

  nativeBuildInputs =
    [
      plex-conan
      #pythonRelaxDepsHook
      setuptools
      pip
      virtualenvwrapper
      wheel
    ];

  propagatedBuildInputs = [ setuptools packaging poyo certifi plex-conan importlib-metadata ];
  doUnpack = false;
  dontUseSetuptoolsCheck = true;
}
