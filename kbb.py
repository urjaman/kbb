#!/usr/bin/env python3

# kbb aka kernel build bot

import os
import sys
import json
import urllib.request
import urllib.error
import shutil
import subprocess


def json_readf(fn):
    with open(fn, "r") as f:
        d = f.read()
    return json.loads(d)


def subX(*args, **kwargs):
    return subprocess.run(*args, **kwargs).returncode == 0


def sub(*args, **kwargs):
    c = subprocess.run(*args, **kwargs).returncode


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
                update_mainline = True
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
            update_mainline = True
        else:
            update_stable.append(r["version"])

print("Update stable:", bool(update_stable), update_stable)
print("Update mainline:", update_mainline)

if update_stable or update_mainline:
    os.chdir("linux")
    if update_mainline:
        print("Fetching mainline")
        if not sub(["git", "fetch", "mainline", "master", "--tags"]):
            sys.exit(1)
        print("Done")

    if update_stable:
        print("Fetching stable(s)")
        targets = ["tags/v" + x for x in update_stable]
        if not sub(["git", "fetch", "stable"] + targets):
            sys.exit(1)
        print("Done")
    os.chdir("..")

kernel_c201 = {
    "dir": "linux",
    "patches": 14,
    "build": "./makepkg-c201-test.sh",
    "branch": "c201-{}_v1",
    "branchfile": "c201-test/git-branch",
}


def doakernel(k):
    pass
