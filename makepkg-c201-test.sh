#!/bin/sh
set -e
set -x
export ARCH="arm"
export CROSS_COMPILE="arm-unknown-linux-gnueabihf-"
export PATH=$PATH:$HOME/x-tools7h/arm-unknown-linux-gnueabihf/bin
cd c201-test
if [ -n "$1" ]; then
	echo $1 > git-tag
fi
makepkg --config ../armv7h-makepkg.conf
