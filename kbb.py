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
import traceback
from subprocess import DEVNULL, PIPE, STDOUT
from email.message import EmailMessage


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

kernel_c201_lts = {
    "dir": "linux-kbb-c201-lts",
    "patchset": "c201",
    "build": "./makepkg-c201-lts.sh",
    "verpolicy": "5.15",
}

kernel_apu_lts = {
    "dir": "linux-kbb-apu",
    "patchset": "apu",
    "build": "./makepkg-apu-lts.sh",
    "verpolicy": "5.10",
}

kernel_i586con = {
    "dir": "linux-kbb-i586con",
    "patchset": "i586con",
    "build": "./i586con-update-kernel.py",
    "verpolicy": "5.15",
}

#kernels = [kernel_c201ml, kernel_c201_stable, kernel_c201_lts, kernel_apu_lts, kernel_i586con]
kernels = [kernel_c201ml, kernel_c201_lts, kernel_apu_lts, kernel_i586con]

url = "https://www.kernel.org/releases.json"

prev2_releases = "old_releases.json"
prev_releases = "prev_releases.json"
curr_fn = "releases.json"

emhost = '\x40tea.urja.dev'
whoami = f'KBB <kbb{emhost}>'
toaddr = f'urja{emhost}, urja\x40urja.dev'
emailproc = ['ssh', 'kbb\x40urja.dev', 'sendmail', '-t']

def vtag4xfer(x):
    return f"refs/tags/v{x}:refs/tags/v{x}"

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

    sniplocator = '*** Waiting for unfinished jobs'

    if log.count('\n') > attach_threshold:
        attach = log;
        log = log.splitlines()
        sniploc = None
        for i in range(len(log)-1,0,-1):
            if sniplocator in log[i]:
                sniploc = i
                break
        if sniploc:
            presnip = "<snip>\n"
            postsnip = "<snip>\n"
            if sniploc < attach_threshold:
                sniploc = attach_threshold
                presnip = ""
            log = log[sniploc-attach_threshold:sniploc]
            if sniploc >= len(log):
                postsnip = ""
            log = presnip + '\n'.join(log) + '\n' + postsnip
        else:
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

def get_current_branch():
    return subc(["git", "branch", "--show-current"], stdout=PIPE).decode().strip()


# Calling rebase and tag "repatch" ... ok.
def repatch_indir(patchset, newver, verpolicy):
    tagname = patchset + "-" + newver
    if os.path.exists(".skipkbb"):
        return False

    if tag_exists(tagname):
        return tagname

    oldtag = subc(["git", "describe", "--tags"], stdout=PIPE).decode().strip()
    (oldset, oldver) = oldtag.split(sep="-", maxsplit=1)

    if '-v' in oldver:
        oldver, _ = oldver.rsplit(sep="-v", maxsplit=1)

    if verpolicy != "mainline":
        newno = versplit(newver)
        oldno = versplit(oldver)
        if newno[0:2] != oldno[0:2]:
            mlvertag = patchset + "-" + str(newno[0]) + "." + str(newno[1])
            if tag_exists(mlvertag):
                branchname = get_current_branch()
                subc(["git", "switch", "-C", branchname, "refs/tags/" + mlvertag])
                (oldset, oldver) = mlvertag.split(sep="-", maxsplit=1)

    if oldset != patchset:
        print(f"Error: this git tree is on a tag for patchset {oldset}, not {patchset}?")
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


def find_new_version(k, rels, update_mainline, update_stable):
    nv = None
    vp = k["verpolicy"]
    if vp == "mainline":
        if update_mainline:
            nv = update_mainline
    elif vp == "stable":
        if rels["latest_stable"]["version"] in update_stable:
            nv = rels["latest_stable"]["version"]
    else:
        for v in update_stable:
            if v.startswith(vp):
                nv = v
    return nv

def kname(k):
    return k["patchset"] + "-" + k["verpolicy"]


def publish_indir(k, nv, tag):
    branch = get_current_branch()
    if tag:
        tagname = tag
    else:
        tagname = k['patchset'] + "-" + nv
    pids = str(os.getpid())
    logfn = "../log/publish-" + kname(k) + "-v" + nv + "_" + pids + ".log"
    print(f"Publishing git tree, log: {logfn}")
    b1 = f"{branch}:refs/heads/{branch}"
    t1 = f"refs/tags/v{nv}:refs/tags/v{nv}"
    t2 = f"refs/tags/{tagname}:refs/tags/{tagname}"
    with open(logfn, "w") as f:
        if not sub(['git','push','-f',"publish", b1, t1, t2], stdin=DEVNULL, stderr=STDOUT, stdout=f):
            mail(f"Publish failure (build success) {kname(k)} {nv}", logfn)

def publish(k, nv, tag=None):
    os.chdir(k['dir'])
    try:
        publish_indir(k, nv, tag)
    except Exception:
        traceback.print_exc()
    os.chdir("..")


def build(k, nv, tag):
    today = datetime.date.today()
    ymd = today.strftime("%y%m%d")
    pids = str(os.getpid())
    logfn = "log/build-" + kname(k) + "-" + ymd + "-v" + nv + "_" + pids + ".log"
    print(f"Building - for details see '{logfn}'")
    with open(logfn, "w") as f:
        if sub([k["build"], tag], stdin=DEVNULL, stderr=STDOUT, stdout=f):
            print("Done. Return value zero (y).")
            print("Running publish()..")
            publish(k, nv, tag)
            print("Done")
            return f"{kname(k)} {nv}"
        else:
            print("Oopsie? Build ended with nonzero return value :(")
            mail(f"Build failure {kname(k)} {nv}", logfn)
            with open("ATTN.txt", "a") as of:
                of.write(logfn + "\n")
            return None


def doakernel(k, rels, update_mainline, update_stable):
    nv = find_new_version(k, rels, update_mainline, update_stable)
    if not nv:
        return None

    print(f"Re/patching {kname(k)} to version {nv}")
    tag = repatch(k["dir"], k["patchset"], nv, k["verpolicy"])
    if not tag:
        print("No tag returned - skipping build")
        return None

    return build(k, nv, tag)

def rebuild_kernel(k):
    # Figure out the version the kernel is "supposed to" be
    os.chdir(k["dir"])
    kv = subc(["git", "describe", "--tags", "--match", "v*", "--exclude", k["patchset"] + '-*' ], stdout=PIPE).decode().strip()
    kv = kv[1:].split(sep='-')
    if kv[1].startswith("rc"):
        kv = kv[0] + '-' + kv[1]
    else:
        kv = kv[0]

    print(f"Determined the kernel version to be {kv}")

    tagbase = k["patchset"] + '-' + kv
    sub(["git", "tag", "-d", tagbase])
    subc(["git", "tag", tagbase])
    print(f"(Re-)created tag {tagbase} - now creating a fresh tag for build processes")

    vnum = 2
    while True:
        buildtag = f"{tagbase}-v{vnum}"
        if tag_exists(buildtag):
            vnum += 1
            continue
        subc(["git", "tag", buildtag])
        break
    print(f"Tag for build: {buildtag}")
    os.chdir('..')
    return build(k, kv, buildtag)


def successmail(successlist):
    if successlist:
        if len(successlist) > 1:
            mail(f"Success building {len(successlist)} kernels", log="\n".join(successlist) + "\n")
        else:
            mail("Success building " + successlist[0], log="\n")

def update_and_build():
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
            subc(["git", "fetch", "mainline", "master", vtag4xfer(update_mainline)])
            print("Done")

        if update_stable:
            print("Fetching stable(s)")
            targets = [vtag4xfer(x) for x in update_stable]
            subc(["git", "fetch", "stable"] + targets)
            print("Done")
        os.chdir("..")

    successlist = []
    for k in kernels:
        r = doakernel(k, rels, update_mainline, update_stable)
        if r:
            successlist.append(r)

    # finally, move prev to old, releases to prev
    os.replace(prev_releases, prev2_releases)
    os.replace(curr_fn, prev_releases)
    successmail(successlist)


if len(sys.argv) == 1:
    update_and_build()
elif len(sys.argv) == 3 and sys.argv[1] == "--rebuild":
    successlist = []
    for k in kernels:
        if kname(k) == sys.argv[2]:
            print(f"Found definition for kernel {kname(k)} - trying to rebuild")
            r = rebuild_kernel(k)
            if r:
                successlist.append(r)
    successmail(successlist)
else:
    print(f"usage: {sys.argv[0]} [--rebuild <patchset-verpolicy>]")
