#!/usr/bin/env python3

import os
import sys
import subprocess
from subprocess import DEVNULL, PIPE, STDOUT

def subc(*args, **kwargs):
    c = subprocess.run(*args, **kwargs)
    if c.returncode != 0:
        print("subprocess failed: ", args)
        print("code:", c.returncode)
        sys.exit(1)
    return c.stdout

def adjust_pkgbuild(dir, ver):
    b = dir + '/PKGBUILD'

    with open(b) as f:
       d = f.readlines()

    vv = ver.split(sep='.')

    with open(b,"w") as f:
        for L in d:
            if len(L) and L[-1] == '\n':
                L = L[:-1]
            c1 = "_srcname="
            c2 = "pkgver="
            brk1 = "md5sums=("
            brk2 = "sha256sums=("
            if L.startswith(c1):
                f.write(f'{c1}linux-{vv[0]}.{vv[1]}\n')
            elif L.startswith(c2):
                f.write(f'{c2}{ver}\n')
            elif L.startswith(brk1) or L.startswith(brk2):
                break
            else:
                f.write(L + '\n')


if len(sys.argv) == 1:
    print(f"usage: {sys.argv[0]} <git-tag> <pkgbuild-dir>")
    sys.exit(1)

[tag, pkgbdir] = sys.argv[1:]

setname,ver = tag.split(sep='-',maxsplit=1)

if "-v" in ver:
    ver,_ = ver.rsplit(sep="-v",maxsplit=1)

pkgbdir = os.path.realpath(pkgbdir)

patchname = pkgbdir + '/' + setname + '.patch'

os.chdir("linux")
basetag = "tags/v" + ver
range = basetag + "..tags/" + tag
count = subc(["git", "rev-list", "--count", range], stdout=PIPE)
count = int(count.decode())

print(f"{count} patches -> {patchname}")

with open(patchname, 'wb') as f:
    subc(["git","format-patch","--stdout", range], stdout=f)

adjust_pkgbuild(pkgbdir, ver)
os.chdir(pkgbdir)
os.system("makepkg -g >> PKGBUILD")
