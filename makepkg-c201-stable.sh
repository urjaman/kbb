#!/bin/sh
set -e
set -x
# Usage: $0 git-tag
[ $# -ge 1 ] || exit 1
export ARCH="arm"
export CROSS_COMPILE="arm-unknown-linux-gnueabihf-"
export PATH=$PATH:$HOME/x-tools7h/arm-unknown-linux-gnueabihf/bin
export MAKEPKG_CONF="$(pwd -P)/armv7h-makepkg.conf"
./patchset-pkgbuild.py "$1" c201-stable
cd c201-stable
makepkg
cd ..
./repothis.sh armv7h c201-stable/*.pkg.tar.*
