#! /bin/bash

set -xe
# This is a workaround the fact that we want to use nix in
# single user mode and purely.
pushd "$1"
nix="$2"

$nix flake check -L --show-trace
$nix build ".#devShells.x86_64-linux.cpp" --show-trace
$nix copy --all --to 's3://cache.plex.bz?compression=zstd&compression-level=15&secret-key=cache.key'
popd
