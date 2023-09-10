#!/bin/sh
set -e
set -x
# Usage: $0 [git-tag]
export ARCH="arm"
export CROSS_COMPILE="arm-unknown-linux-gnueabihf-"
export PATH=$PATH:$HOME/x-tools7h/arm-unknown-linux-gnueabihf/bin
export MAKEPKG_CONF="$(pwd -P)/armv7h-makepkg.conf"
if [ -n "$1" ]; then
	./patchset-pkgbuild.py "$1" c201-stable
fi
cd c201-stable
makepkg -C
cd ..
./repothis.sh armv7h c201-stable/*.pkg.tar.*
