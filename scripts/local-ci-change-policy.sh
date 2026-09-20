#!/usr/bin/env bash
# Fail closed when a change is too risky for local (actor-scoped) certification.
#
# This is half of the cheap-CI lane. Its only job is to answer one question:
# "is a local pass genuinely as good as a cloud pass for THIS diff?" It says no
# by default. Widening it to make your change eligible defeats the mechanism.
#
# Configure the risk surface for your project in RISK_PATTERN below.
set -euo pipefail

if [[ "$#" -ne 2 ]]; then
  echo "usage: $0 <base-sha> <head-sha>" >&2
  exit 2
fi

base_sha="$1"
head_sha="$2"

MAX_FILES="${LOCAL_CI_MAX_FILES:-80}"
MAX_MODULES="${LOCAL_CI_MAX_MODULES:-3}"
# {{CUSTOMIZE}} — every path here always goes to cloud CI.
RISK_PATTERN="${LOCAL_CI_RISK_PATTERN:-^\.github/|(^|/)migrations/|(^|/)(requirements[^/]*\.txt|package-lock\.json|pubspec\.lock|go\.sum|Gemfile\.lock|Dockerfile[^/]*|docker-compose[^/]*\.ya?ml)$|(^|/)(settings|config)/|(^|/)[^/]*(auth|permission|isolation|tenant|billing|payment|compliance|jwt|crypto|secret)[^/]*\.(py|ts|tsx|dart|go|rb|kt|swift)$|^scripts/(check_|deploy|local-ci)|^CLAUDE\.md$}"
# {{CUSTOMIZE}} — how a path maps to a "module" for the module-count cap.
MODULE_REGEX="${LOCAL_CI_MODULE_REGEX:-s#^backend/apps/([^/]+)/.*#\1#p}"

changed_files=()
while IFS= read -r path; do
  changed_files+=("$path")
done < <(git diff --name-only "$base_sha" "$head_sha")

if [[ "${#changed_files[@]}" -eq 0 ]]; then
  echo "POLICY_NO_CHANGED_FILES: rejected: no changed files." >&2
  exit 1
fi

if [[ "${#changed_files[@]}" -gt "$MAX_FILES" ]]; then
  echo "POLICY_FILE_LIMIT: rejected: ${#changed_files[@]} files exceed the ${MAX_FILES}-file limit." >&2
  exit 1
fi

for path in "${changed_files[@]}"; do
  if [[ "$path" =~ $RISK_PATTERN ]]; then
    echo "POLICY_HIGH_RISK_PATH: rejected: high-risk path $path requires cloud CI." >&2
    exit 1
  fi
done

modules=()
while IFS= read -r mod; do
  [[ -n "$mod" ]] && modules+=("$mod")
done < <(printf '%s\n' "${changed_files[@]}" | sed -nE "$MODULE_REGEX" | sort -u)

if [[ "${#modules[@]}" -gt "$MAX_MODULES" ]]; then
  echo "POLICY_MODULE_LIMIT: rejected: ${#modules[@]} modules exceed the ${MAX_MODULES}-module limit." >&2
  exit 1
fi

echo "Local CI change policy: eligible (${#changed_files[@]} files)."
