#!/usr/bin/env bash
# enforce-file-size.sh <mode>
#
# Enforces the CLAUDE.md rule: no source file over 1000 lines.
#   mode = pre   -> PreToolUse(Write): DENY writing >1000-line content.
#   mode = post  -> PostToolUse(Edit|Write): WARN (exit 2 -> fed back to Claude)
#                   when the resulting file exceeds 1000 lines.
#
# Reads the hook JSON payload on stdin. Fails open: any internal error exits 0
# so the guardrail can never wedge a legitimate edit.

MODE="${1:-post}"
LIMIT=1000

input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_response.filePath // empty' 2>/dev/null)"
[ -z "$file" ] && exit 0

# Only source code is subject to the ceiling.
case "$file" in
  *.py|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs) ;;
  *) exit 0 ;;
esac

# Exempt DB migrations, generated code, and vendored trees — these are allowed
# to be large and are not "one concern" modules.
case "$file" in
  */migrations/*|*/tests/*|*/__tests__/*|*/node_modules/*|*/.next/*|*.d.ts) exit 0 ;;
esac
# Exempt test files by BASENAME only (test_*.py, *_test.py, *.test.ts, *.spec.ts)
# so real source like ab_test_services.py is NOT skipped.
base="${file##*/}"
case "$base" in
  test_*|*_test.py|*.test.*|*.spec.*) exit 0 ;;
esac

if [ "$MODE" = "pre" ]; then
  # Count lines in the content about to be written (Write tool only).
  lines="$(printf '%s' "$input" | jq -r '.tool_input.content // ""' 2>/dev/null | grep -c '' 2>/dev/null)"
  [ -z "$lines" ] && exit 0
  if [ "$lines" -gt "$LIMIT" ]; then
    reason="Refusing to write ${file}: ${lines} lines exceeds the ${LIMIT}-line ceiling (CLAUDE.md: never create a file over ~400 lines, never grow past 1000). Split it into an orchestrator plus focused, single-concern modules before writing."
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}\n' \
      "$(printf '%s' "$reason" | jq -Rs .)"
  fi
  exit 0
fi

# post mode: the file now exists on disk — measure it.
[ -f "$file" ] || exit 0
lines="$(grep -c '' "$file" 2>/dev/null)"
[ -z "$lines" ] && exit 0
if [ "$lines" -gt "$LIMIT" ]; then
  echo "File-size guardrail: ${file} is now ${lines} lines (> ${LIMIT}). Per CLAUDE.md this file must be split — extract a focused module (orchestrator + single-concern helpers) rather than growing it further." >&2
  exit 2
fi
exit 0
