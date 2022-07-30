#!/bin/sh
set -e
set -x
# Usage: $0 git-tag
[ $# -ge 1 ] || exit 1
export MAKEPKG_CONF="$(pwd -P)/x86_64-makepkg.conf"
./patchset-pkgbuild.py "$1" apu-lts
cd apu-lts
makepkg
cd ..
./repothis.sh x86_64 apu-lts/*.pkg.tar.*
