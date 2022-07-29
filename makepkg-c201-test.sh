#!/bin/sh
set -e
set -x
export ARCH="arm"
export CROSS_COMPILE="arm-unknown-linux-gnueabihf-"
export PATH=$PATH:$HOME/x-tools7h/arm-unknown-linux-gnueabihf/bin
cd c201-test
makepkg --config ../armv7h-makepkg.conf
cd ..
./repothis.sh armv7h c201-test/*.pkg.tar.*
