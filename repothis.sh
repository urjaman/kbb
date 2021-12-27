#!/bin/bash
[ $# -ge 2 ] || exit 1
# Usage: repothis.sh arch package [package..]
mkdir -p kbbpkgs-mp pkgarchive
sshfs urja.dev:srv/kbbpkgs kbbpkgs-mp
PARCH="$1"
shift 1
while [ -n "$1" ]; do
	cp "$1" "kbbpkgs-mp/$PARCH/"
	mv "$1" pkgarchive/
	PKG=$(basename $1)
	cd "kbbpkgs-mp/$PARCH/"
	repo-add -R kbbpkgs.db.tar.gz "$PKG"
	cd ../..
	shift 1
done
fusermount -u kbbpkgs-mp
exit 0
