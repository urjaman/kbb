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


def adjust_brcfg(cfg, ver):
    with open(cfg) as f:
       d = f.readlines()

    config_names = [ "BR2_LINUX_KERNEL_VERSION", "BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE" ]
    found = False
    with open(cfg,"w") as f:
        for L in d:
            for c in config_names:
                if L.startswith(c):
                    f.write(f'{c}="{ver}"\n')
                    found = True
                    break
            else:
                f.write(L.strip() + '\n')
    if not found:
        sys.exit(f"Nothing adjustable found in {cfg}?!?")



if len(sys.argv) == 1:
    print(f"usage: {sys.argv[0]} <git-tag>")
    sys.exit(1)

[tag] = sys.argv[1:]

_,ver = tag.split(sep='-',maxsplit=1)

if "-v" in ver:
    ver,_ = ver.rsplit(sep="-v",maxsplit=1)

i586con_dir = "/home/urjaman/bulk/i586con"
patchpfx = "brext/global-patches/linux/" + ver
patchdir = i586con_dir + "/" + patchpfx

os.chdir("linux-kbb-i586con")
basetag = "tags/v" + ver
count = subc(["git", "rev-list", "--count", basetag + "..HEAD"], stdout=PIPE)
count = int(count.decode())

try:
    os.mkdir(patchdir)
except FileExistsError:
    subc(["rm", "-rf", patchdir])
    os.mkdir(patchdir)

subc(["git","format-patch","-o", patchdir, "-" + str(count)])

build_list = [ ]
with os.scandir(i586con_dir) as entries:
    for entry in entries:
        if entry.name.startswith("Build-"):
            build_list.append([entry.stat().st_mtime, entry.path])

build_list.sort(reverse=True, key=lambda e: e[0]) # sort by mtime

if not build_list:
    sys.exit("Couldn't find an i586con build dir to test-build kernel in")

os.chdir(build_list[0][1])

adjust_brcfg(".config", ver)
subc(["rm", "-rf", "target/usr/lib/modules"])
subc(["make"])
os.chdir(i586con_dir)
defcfg = "brext/configs/i586con_defconfig"
adjust_brcfg(defcfg, ver)
if not tag.startswith("nocommit"):
    subc(["git", "add", patchpfx, defcfg])
    subc(["git", "commit", "-m", f"KBB: Automatic update to linux {ver}"])

with open(".rebuild-once","w") as f:
    f.write(f"linux {ver}")

