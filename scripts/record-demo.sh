#!/usr/bin/env bash
# Record a proof video of the current demo spec.
#
#   ./scripts/record-demo.sh [slug]
#
# Env:
#   DEMO_BASE_URL     app URL (default http://localhost:3500 — this repo's
#                     Docker frontend port; NOT 3000)
#   DEMO_NO_SERVER=1  skip the docker-compose readiness check (recording
#                     against QA or another deployed URL)
#   DEMO_UPLOAD_CMD   optional; receives the video path, must print a URL
#
# Why this brings the stack up itself rather than using Playwright's
# `webServer`: the dev server here is `docker compose`, and `docker compose up
# -d` returns immediately. Playwright would see the process exit and call the
# server dead. So readiness is settled before Playwright is invoked.
set -euo pipefail

SLUG="${1:-demo}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BASE_URL="${DEMO_BASE_URL:-http://localhost:3500}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR=".demos/out"
mkdir -p "$OUT_DIR"
rm -rf .demos/raw

if [ -z "${DEMO_NO_SERVER:-}" ]; then
  # The Docker CLI on this machine may be an old Homebrew build that cannot
  # talk to the current daemon; prefer Docker Desktop's own binary when present.
  if [ -x /Applications/Docker.app/Contents/Resources/bin/docker ]; then
    export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
  fi

  echo "==> Ensuring the local stack is up..."
  docker compose up -d frontend backend >/dev/null 2>&1 || true

  echo "==> Waiting for $BASE_URL ..."
  for _ in $(seq 1 60); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL" || echo 000)"
    # 2xx/3xx both mean "serving" — the app 307s to /login when signed out.
    if [ "$code" != "000" ] && [ "${code:0:1}" != "5" ]; then
      echo "    ready (HTTP $code)"
      break
    fi
    sleep 2
  done
  if [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL" || echo 000)" = "000" ]; then
    echo "FAILED: $BASE_URL never came up. Start the stack, or set DEMO_NO_SERVER=1" >&2
    echo "        if you meant to record against a deployed URL." >&2
    exit 1
  fi
fi

echo "==> Running demo spec..."
# Playwright lives in frontend/ (there is no root package.json), so the runner
# is invoked from there and paths in the config are frontend-relative.
if ! (cd frontend && DEMO_SPEC="${DEMO_SPEC:-}" DEMO_BASE_URL="$BASE_URL" npx playwright test --config=playwright.demo.config.ts); then
  echo "" >&2
  echo "FAILED: the walkthrough did not pass. No proof video produced." >&2
  echo "This is the point — a video of a broken flow is not proof." >&2
  exit 1
fi

WEBM="$(find .demos/raw -type f -name '*.webm' -exec ls -t {} + 2>/dev/null | head -n1 || true)"
if [ -z "$WEBM" ]; then
  echo "FAILED: the spec passed but no video was written. Check 'video' in frontend/playwright.demo.config.ts." >&2
  exit 1
fi

if command -v ffmpeg >/dev/null 2>&1; then
  TARGET="$OUT_DIR/${SLUG}-${STAMP}.mp4"
  echo "==> Encoding mp4..."
  ffmpeg -loglevel error -y -i "$WEBM" \
    -vf "scale=1280:-2,fps=24" \
    -c:v libx264 -preset veryfast -crf 26 \
    -pix_fmt yuv420p -movflags +faststart \
    "$TARGET"
else
  echo "==> ffmpeg not found, keeping webm (fine for Slack/Drive, not for Safari)."
  TARGET="$OUT_DIR/${SLUG}-${STAMP}.webm"
  cp "$WEBM" "$TARGET"
fi

echo ""
echo "PROOF VIDEO: $TARGET"

if [ -n "${DEMO_UPLOAD_CMD:-}" ]; then
  echo "==> Uploading..."
  URL="$("$DEMO_UPLOAD_CMD" "$TARGET")"
  echo "SHAREABLE LINK: $URL"
fi
