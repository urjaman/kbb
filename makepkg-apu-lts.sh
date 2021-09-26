#!/bin/sh
set -e
set -x
cd apu-lts
if [ -n "$1" ]; then
	echo $1 > git-tag
fi
makepkg --config ../x86_64-makepkg.conf
cd ..
./repothis.sh x86_64 apu-lts/*.pkg.tar.*
