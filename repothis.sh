#!/bin/bash
[ $# == 2 ] || exit 1
# Usage: repothis.sh arch package
mkdir -p kbbpkgs-mp pkgarchive
sshfs urja.dev:srv/kbbpkgs kbbpkgs-mp
cp "$2" "kbbpkgs-mp/$1/"
mv "$2" pkgarchive/
PKG=$(basename $2)
cd "kbbpkgs-mp/$1/"
repo-add -R kbbpkgs.db.tar.gz "$PKG"
cd ../..
fusermount -u kbbpkgs-mp
exit 0
