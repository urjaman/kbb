#!/bin/sh
set -e
set -x
# Usage: $0 [git-tag]
export MAKEPKG_CONF="$(pwd -P)/x86_64-makepkg.conf"
if [ -n "$1" ]; then
	./patchset-pkgbuild.py "$1" apu-lts
fi
cd apu-lts
makepkg -C
cd ..
./repothis.sh x86_64 apu-lts/*.pkg.tar.*
