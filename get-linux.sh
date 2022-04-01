#!/bin/bash
set -x
set -e
git clone --bare git@github.com:urjaman/linux-for-my-autobuilder.git linux
cd linux
git remote rename origin publish || true
echo "The fail to unset remote.publish.fetch is okay, methinks"
git remote add stable https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
git remote add mainline https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
git worktree add ../linux-kbb-apu
git worktree add ../linux-kbb-c201
git worktree add ../linux-kbb-c201-lts
git worktree add ../linux-kbb-c201-stable
git worktree add ../linux-kbb-i586con
