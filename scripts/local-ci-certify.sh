#!/usr/bin/env bash
# Run the CI checks on this machine, scoped to what the branch changed, and
# publish a `local/fast-ci` commit status so cloud CI can skip the same work.
#
# TEMPLATE. The generic half (preconditions, eligibility, status publishing) is
# done. Fill in the STACK-SPECIFIC CHECKS block for your project, and make your
# CI's first job read the status and short-circuit when it is `success`.
#
#   scripts/local-ci-certify.sh --push       # run checks, certify, then push
#   scripts/local-ci-certify.sh --dry-run    # print what would run
#
# `--push` is the safe order: the commit is published only after checks pass.
set -euo pipefail

TRUNK="${LOCAL_CI_TRUNK:-origin/main}"
CONTEXT="local/fast-ci"
DRY_RUN=0
PUSH=0
BASE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --push) PUSH=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --base) BASE="$2"; shift ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
  shift
done

root="$(git rev-parse --show-toplevel)"
cd "$root"
base_ref="${BASE:-$TRUNK}"
head_sha="$(git rev-parse HEAD)"

die() { echo "✖ $*" >&2; exit 1; }
run() {
  echo "→ $*"
  [[ "$DRY_RUN" -eq 1 ]] || "$@"
}

# ---------------------------------------------------------------- preconditions
# Each of these will stop you the first time. That is the point: a certification
# that can be produced from a dirty or stale tree certifies nothing.
[[ -z "$(git status --porcelain)" ]] || die "worktree not clean (untracked files count). Try: git stash -u"
git rev-parse --verify --quiet "$base_ref" >/dev/null || die "no such ref: $base_ref (git fetch?)"
merge_base="$(git merge-base "$base_ref" HEAD)"
[[ "$merge_base" == "$(git rev-parse "$base_ref")" ]] \
  || die "branch is not based on the current $base_ref — rebase first"

bash scripts/local-ci-change-policy.sh "$merge_base" "$head_sha" \
  || die "not eligible for the local lane — push and let cloud CI run"

changed="$(git diff --name-only "$merge_base" "$head_sha")"
echo "Changed files:"; echo "$changed" | sed 's/^/  /'

# ------------------------------------------------------- always-on repo gates
run python3 scripts/check_code_size.py --base "$merge_base"
run python3 scripts/check_known_failures.py

# ==========================================================================
# STACK-SPECIFIC CHECKS  — {{CUSTOMIZE}}
# Keep these SCOPED TO THE DIFF. The whole value of this lane is that it runs
# the same assertions cloud CI would, over a fraction of the surface. Copy the
# block for your stack out of docs/stacks/<profile>.md.
#
# Example (Python + TypeScript web profile):
#   if grep -q '^backend/' <<<"$changed"; then
#     run python3 scripts/check_isolation.py --base "$merge_base"
#     run "$PY" backend/manage.py makemigrations --check --dry-run
#     run "$PY" -m mypy apps common config
#     run "$PY" -m pytest <changed apps' tests> -q
#   fi
#   if grep -q '^frontend/' <<<"$changed"; then
#     run npx tsc --noEmit
#     run npx jest --findRelatedTests $(grep '^frontend/' <<<"$changed")
#     run npm run build
#   fi
#
# Example (Flutter profile):
#   run flutter analyze
#   run flutter test
# ==========================================================================

echo "✓ all checks passed"
[[ "$DRY_RUN" -eq 1 ]] && exit 0

# Re-check the trunk did not move while the run was in flight.
git fetch --quiet origin || true
[[ "$(git merge-base "$base_ref" HEAD)" == "$(git rev-parse "$base_ref")" ]] \
  || die "$base_ref moved during the run — rebase and re-certify"

if [[ "$PUSH" -eq 1 ]]; then
  git push origin "HEAD:$(git rev-parse --abbrev-ref HEAD)"
fi

# A status cannot be attached to a commit the remote has never seen — this is
# why --push is the recommended order.
gh api --method POST "repos/{owner}/{repo}/statuses/${head_sha}" \
  -f state=success \
  -f context="$CONTEXT" \
  -f description="local CI passed ($(date -u +%FT%TZ))" >/dev/null \
  && echo "✓ published $CONTEXT on ${head_sha:0:12}"
