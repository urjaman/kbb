#!/bin/sh
set -e
set -x
cd apu-lts
if [ -n "$1" ]; then
	echo $1 > git-tag
fi
makepkg
