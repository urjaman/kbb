#!/bin/sh
set -e
set -x
export ARCH="arm"
export CROSS_COMPILE="arm-unknown-linux-gnueabihf-"
export PATH=$PATH:$HOME/x-tools7h/arm-unknown-linux-gnueabihf/bin
./patchset-pkgbuild.py "$1" c201-stable
cd c201-stable
makepkg --config ../armv7h-makepkg.conf
cd ..
./repothis.sh armv7h c201-stable/*.pkg.tar.*
