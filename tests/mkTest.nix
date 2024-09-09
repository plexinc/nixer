{ pname, stdenv }: params:
stdenv.mkDerivation ({
  inherit pname;
  version = "0.0.0.dummy";
  doCheck = true;
  installPhase = ''
    mkdir $out
  '';
} // params)
