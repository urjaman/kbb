#!/bin/bash
if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <target version>"
	exit 1
fi
set -e
cd c201-test
echo "fetch"
git fetch origin
echo "push tag and test tag existence"
git push upstream tags/v$1
echo "checkout new branch"
git checkout -b c201-$1_v1
echo "rebase to tag"
git rebase -i tags/v$1
echo "push result up to github"
git push upstream
echo "Success."
