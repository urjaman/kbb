#!/usr/bin/env python3

# kbb aka kernel build bot
# but not referred to with the full name,
# since there's many a "kernel build bot" out there...
# but I dont have a name really, so ... kbb.py it is.

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
from email.message import EmailMessage


url = "https://www.kernel.org/releases.json"

prev_releases = "prev_releases.json"
curr_fn = "releases.json"

whoami = 'KBB <kbb@urja.dev>'
toaddr = 'urja@urja.dev, urjaman@gmail.com'
emailproc = ['ssh', 'kbb@urja.dev', 'sendmail', '-t']

def htmlize(s):
    escapes = {
        '&': '&amp;',
        '>': '&gt;',
        '<': '&lt;'
    }
    prefix = '<html><head></head><body><pre>\n'
    suffix = '</pre></body></html>\n'
    for k in escapes:
        s = s.replace(k, escapes[k])
    return prefix + s + suffix

def mail(subj, logfn = None, log = None):
    if logfn:
        with open(logfn) as f:
            log = f.read()

    attach_threshold = 25
    msg = EmailMessage()
    msg['Subject'] = '[KBB] ' + subj
    msg['From'] = whoami
    msg['To'] = toaddr

    if log.count('\n') > attach_threshold:
        attach = log;
        log = log.splitlines()
        log = log[-attach_threshold:]
        log = '<snip>\n' + '\n'.join(log) + '\n'
    else:
        attach = None

    msg.set_content(log)
    msg.add_alternative(htmlize(log), subtype='html')
    if attach:
        msg.add_attachment(attach, filename='log.txt', cte='quoted-printable')

    #print(msg)
    subprocess.run(emailproc, input=msg.as_bytes())


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


def versplit(ver):
    return [int(x) if x.isdigit() else x for x in ver.split(sep=".")]


def tag_exists(tag):
    return sub(["git", "rev-parse", "refs/tags/" + tag], stdout=DEVNULL, stderr=DEVNULL)


# Calling rebase and tag "repatch" ... ok.
def repatch_indir(patchset, newver, verpolicy):
    tagname = patchset + "-" + newver
    if os.path.exists(".skipkbb"):
        return False

    if tag_exists(tagname):
        return tagname

    oldtag = subc(["git", "describe", "--tags"], stdout=PIPE).decode().strip()
    (oldset, oldver) = oldtag.split(sep="-", maxsplit=1)

    if verpolicy != "mainline":
        newno = versplit(newver)
        oldno = versplit(oldver)
        if newno[0:2] != oldno[0:2]:
            mlvertag = patchset + "-" + str(newno[0]) + "." + str(newno[1])
            if tag_exists(mlvertag):
                branchname = (
                    subc(["git", "branch", "--show-current"], stdout=PIPE)
                    .decode()
                    .strip()
                )
                subc(["git", "switch", "-C", branchname, "refs/tags/" + mlvertag])
                (oldset, oldver) = mlvertag.split(sep="-", maxsplit=1)

    if oldset != patchset:
        print("Error: this git tree is on a tag for patchset {oldset}, not {patchset}?")
        return False

    oldvertag = "tags/v" + oldver

    patches = subc(["git", "rev-list", "--count", oldvertag + "..HEAD"], stdout=PIPE)
    patches = int(patches.decode())

    vertag = "tags/v" + newver

    rebase_cmd = ["git", "rebase", "HEAD~" + str(patches), "--onto", vertag]
    rebase_log = ".kbb-rebase-log"
    rbproc = subprocess.Popen(rebase_cmd, stdin=DEVNULL, stderr=STDOUT, stdout=PIPE)
    tee = subprocess.Popen(["tee", rebase_log], stdin=rbproc.stdout)
    r1 = rbproc.wait()
    tee.wait()
    if r1:
        mail("Uhh, rebase trouble with " + tagname, rebase_log)
        print(
            "Finish rebase manually. Use 'touch .skipkbb' to skip this kernel for now instead."
        )
        sub(["/bin/bash"])

    if os.path.exists(".skipkbb"):
        return False

    count = subc(["git", "rev-list", "--count", vertag + "..HEAD"], stdout=PIPE)
    count = int(count.decode())
    if count != patches:
        print(f"Info: patchset {patchset} now (version {newver}) has {count} patches.")

    subc(["git", "tag", tagname])
    return tagname


def repatch(dir, patchset, newver, verpolicy):
    os.chdir(dir)
    r = repatch_indir(patchset, newver, verpolicy)
    os.chdir("..")
    return r


successlist = []

def doakernel(k):
    global successlist

    nv = None
    vp = k["verpolicy"]
    if vp == "mainline":
        if update_mainline:
            nv = update_mainline
        else:
            return
    elif vp == "stable":
        if rels["latest_stable"]["version"] in update_stable:
            nv = rels["latest_stable"]["version"]
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
    tag = repatch(k["dir"], k["patchset"], nv, vp)
    if not tag:
        print("No tag returned - skipping build")
        return
    today = datetime.date.today()
    ymd = today.strftime("%y%m%d")
    pids = str(os.getpid())
    logfn = "log/build-" + kname + "-" + ymd + "-v" + nv + " " + pids + ".log"
    print(f"Building - for details see '{logfn}'")
    with open(logfn, "w") as f:
        if sub([k["build"], tag], stdin=DEVNULL, stderr=STDOUT, stdout=f):
            print("Done. Return value zero (y).")
            successlist.append(f"{kname} {nv}")
        else:
            print("Oopsie? Build ended with nonzero return value :(")
            mail(f"Build failure {kname} {nv}", logfn)
            with open("ATTN.txt", "a") as of:
                of.write(logfn + "\n")


kernel_c201ml = {
    "dir": "linux-kbb-c201",
    "patchset": "c201",
    "build": "./makepkg-c201-test.sh",
    "verpolicy": "mainline",
}

kernel_c201_stable = {
    "dir": "linux-kbb-c201-stable",
    "patchset": "c201",
    "build": "./makepkg-c201-stable.sh",
    "verpolicy": "stable",
}


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
    verno = versplit(r["version"])
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
        oldver = versplit(o["version"])
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
        subc(["git", "fetch", "--tags", "stable"] + targets)
        print("Done")
    os.chdir("..")




doakernel(kernel_c201ml)
doakernel(kernel_c201_stable)

# finally, move releases to prev
os.replace(curr_fn, prev_releases)

if successlist:
    if len(successlist) > 1:
        mail(f"Success building {len(successlist)} kernels", log="\n".join(successlist) + "\n")
    else:
        mail("Success building " + successlist[0], log="\n")
