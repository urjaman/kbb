#!/bin/sh
set -e
set -x
export ARCH="arm"
export CROSS_COMPILE="arm-unknown-linux-gnueabihf-"
export PATH=$PATH:$HOME/x-tools7h/arm-unknown-linux-gnueabihf/bin
export MAKEPKG_CONF="$(pwd -P)/armv7h-makepkg.conf"
cd c201-test
makepkg -s
cd ..
./repothis.sh armv7h c201-test/*.pkg.tar.*
