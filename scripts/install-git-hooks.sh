#!/usr/bin/env bash
# Point this clone at the repo's tracked hooks. Run once per machine/clone.
#
# Deliberately an ABSOLUTE path. `core.hooksPath` is resolved relative to the
# working tree it is used from, so a relative value only works in worktrees
# whose checked-out branch actually contains `.githooks/`. This repo runs
# dozens of long-lived worktrees on older branches; with a relative path they
# silently run no hook at all, which is the exact failure this hook exists to
# prevent. An absolute path into the main clone covers every worktree.
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
cd "$root"

if [ ! -x ".githooks/pre-push" ]; then
    echo "error: .githooks/pre-push not found or not executable in ${root}." >&2
    echo "       Run this from a checkout whose branch contains .githooks/." >&2
    exit 1
fi

git config core.hooksPath "${root}/.githooks"
echo "core.hooksPath -> ${root}/.githooks"
echo "Active hooks:"
ls -1 .githooks | sed 's/^/  /'
echo
echo "Covers this clone and all of its worktrees:"
git worktree list | wc -l | xargs echo "  worktrees:"
