{ lib
, config
, ...
}:
with lib;
{
  imports = [
  ];

  options = {
    nixer.hello = {
      who = mkOption {
        type = types.str;
        default = "Nixer";
        description = ''
          Who to greet
        '';
      };
    };
  };

  config = {
    perSystem = { self, pkgs, system, ... }:
      let
        greeting = pkgs.writeScript "my-hello" ''
          #! ${pkgs.stdenv.shell}
          ${pkgs.hello}/bin/hello -g 'Hello ${config.nixer.hello.who}'
        '';
        my-hello = builtins.trace "my-hello-${pkgs.stdenv.hostPlatform.libc}" "my-hello-${pkgs.stdenv.hostPlatform.libc}";
      in
      {
        packages.default = pkgs.hello;
        packages.${my-hello} = greeting;

        apps.default = {
          type = "app";
          program = "${greeting}";
        };
      };
  };
}
