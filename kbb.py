#!/usr/bin/env python3

# kbb aka kernel build bot

import os
import sys
import json
import urllib.request
import urllib.error
import shutil
import subprocess
import time
import datetime
from subprocess import DEVNULL, PIPE, STDOUT


def json_readf(fn):
    with open(fn, "r") as f:
        d = f.read()
    return json.loads(d)


def sub(*args, **kwargs):
    c = subprocess.run(*args, **kwargs)
    if c.returncode != 0:
        return False
    if c.stdout:
        return c.stdout
    return True


def subc(*args, **kwargs):
    c = subprocess.run(*args, **kwargs)
    if c.returncode != 0:
        print("subprocess failed: ", args)
        print("code:", c.returncode)
        sys.exit(1)
    return c.stdout


url = "https://www.kernel.org/releases.json"

prev_releases = "prev_releases.json"
curr_fn = "releases.json"

if not os.path.exists(curr_fn):
    r = urllib.request.urlopen(url, timeout=30)
    with open(curr_fn, "w+b") as t:
        shutil.copyfileobj(r, t)

if not os.path.exists(prev_releases):
    os.rename(curr_fn, prev_releases)
    sys.exit(0)

rels = json_readf(curr_fn)
prevs = json_readf(prev_releases)

update_stable = []
update_mainline = False
for r in rels["releases"]:
    if not r["version"][0].isdigit():
        continue
    verno = [int(x) if x.isdigit() else x for x in r["version"].split(sep=".")]
    print(r["moniker"], verno)
    found = False
    for o in prevs["releases"]:
        # mainline is just compared to mainline, rest to matching 2 numbers of version
        if r["moniker"] == "mainline":
            if o["moniker"] != "mainline":
                continue
            found = True
            if r["version"] != o["version"]:
                update_mainline = r["version"]
            break
        if o["moniker"] == "mainline":
            continue
        oldver = [int(x) for x in o["version"].split(sep=".")]
        if oldver[0:2] == verno[0:2]:
            found = True
            if o["version"] != r["version"]:
                update_stable.append(r["version"])
            break
    if not found:
        if r["moniker"] == "mainline":
            update_mainline = r["version"]
        else:
            update_stable.append(r["version"])

print("Update stable:", bool(update_stable), update_stable)
print("Update mainline:", bool(update_mainline), update_mainline)

if update_stable or update_mainline:
    os.chdir("linux")
    if update_mainline:
        print("Fetching mainline")
        subc(["git", "fetch", "mainline", "master", "--tags"])
        print("Done")

    if update_stable:
        print("Fetching stable(s)")
        targets = ["tags/v" + x for x in update_stable]
        subc(["git", "fetch", "stable"] + targets)
        print("Done")
    os.chdir("..")

kernel_c201ml = {
    "dir": "linux-kbb-c201",
    "patchset": "c201",
    "patches": 14,
    "build": "./makepkg-c201-test.sh",
    "verpolicy": "mainline",
}

# Calling rebase and tag "repatch" ... ok.
def repatch_indir(patchset, patches, newver):
    kbbpatchcnt = ".kbb_patchcount"

    tagname = patchset + "-" + newver
    if os.path.exists(".skipkbb"):
        return False

    if sub(
        ["git", "rev-parse", "refs/tags/" + tagname], stdout=DEVNULL, stderr=DEVNULL
    ):
        return tagname

    if os.path.exists(kbbpatchcnt):
        with open(kbbpatchcnt) as f:
            patches = int(f.read())

    vertag = "tags/v" + newver

    if not sub(["git", "rebase", "HEAD~" + str(patches), "--onto", vertag]):
        print(
            "Finish rebase manually. Use 'touch .skipkbb' to skip this kernel for now instead."
        )
        sub(["/bin/bash"])

    if os.path.exists(".skipkbb"):
        return False

    count = subc(["git", "rev-list", "--count", vertag + "..HEAD"], stdout=PIPE)
    count = int(count.decode())
    if count != patches:
        print(
            f"Warning: patchset {patchset} now (version {newver}) has {count} patches!"
        )
        with open(kbbpatchcnt, "w") as f:
            f.write(str(count))

    subc(["git", "tag", tagname])
    return tagname


def repatch(dir, patchset, patches, newver):
    os.chdir(dir)
    r = repatch_indir(patchset, patches, newver)
    os.chdir("..")
    return r


def doakernel(k):
    nv = None
    vp = k["verpolicy"]
    if vp == "mainline":
        if update_mainline:
            nv = update_mainline
        else:
            return
    elif vp == "stable":
        if rels["latest_stable"] in update_stable:
            vp = rels["latest_stable"]
        else:
            return
    else:
        for v in update_stable:
            if v.startswith(vp):
                nv = v
    if not nv:
        return
    kname = k["patchset"] + "-" + vp
    print(f"Re/patching {kname} to version {nv}")
    tag = repatch(k["dir"], k["patchset"], k["patches"], nv)
    if not tag:
        print("No tag returned - skipping build")
        return
    today = datetime.date.today()
    ymd = today.strftime("%y%m%d")
    pids = str(os.getpid())
    logfn = "kbb-build-" + kname + "-" + ymd + "-v" + nv + " " + pids + ".log"
    print(f"Building - for details see '{logfn}'")
    with open(logfn, "w") as f:
        if sub([k["build"], tag], stdin=DEVNULL, stderr=STDOUT, stdout=f):
            print("Done. Return value zero (y).")
        else:
            print("Oopsie? Build ended with nonzero return value :(")
            with open("ATTN.txt","a") as of:
                of.write(logfn + '\n')


doakernel(kernel_c201ml)

# finally, move releases to prev
os.replace(curr_fn, prev_releases)
