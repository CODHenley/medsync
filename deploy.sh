#!/bin/zsh
# MedSync deploy — clears stale git locks, commits, and pushes
# Usage: ./deploy.sh "your commit message"
cd ~/Downloads/medsync_deploy
rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
git add -A
git commit -m "${1:-update}"
git push
