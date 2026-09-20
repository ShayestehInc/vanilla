#!/usr/bin/env python3
"""Archive a completed pipeline run's stage artifacts into ``tasks/archive/<slug>/``.

Why this exists
---------------
``tasks/`` had grown to 61 files with no lifecycle -- March artifacts beside
today's, and five competing ``dev-done*`` variants for a path every downstream
skill reads as a bare literal. The fix is not "be tidier": it is that finishing a
run has a command, so the next run starts from a clean, unambiguous set.

Usage
-----
    python scripts/archive_artifacts.py --slug whatsapp-dual-identity
    python scripts/archive_artifacts.py --slug foo --dry-run
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from pipeline_status import ARTIFACTS, REPO_ROOT

TASKS_DIR = REPO_ROOT / "tasks"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _git_mv(source: Path, target: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"would move {source.relative_to(REPO_ROOT)} -> "
              f"{target.relative_to(REPO_ROOT)}")
        return
    subprocess.run(["git", "mv", str(source), str(target)], cwd=REPO_ROOT, check=True)
    print(f"archived {target.relative_to(REPO_ROOT)}")


def archive(slug: str, dry_run: bool) -> int:
    """Move every present canonical artifact into ``tasks/archive/<slug>/``."""
    destination = TASKS_DIR / "archive" / slug
    present = [(TASKS_DIR / name) for name, _ in ARTIFACTS if (TASKS_DIR / name).exists()]
    if not present:
        print("No canonical stage artifacts present — nothing to archive.")
        return 0
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
    for source in present:
        _git_mv(source, destination / source.name, dry_run)
    print(f"\n{len(present)} artifact(s) -> tasks/archive/{slug}/")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True, help="kebab-case name for the run")
    parser.add_argument("--dry-run", action="store_true", help="print, do not move")
    args = parser.parse_args()

    if not SLUG_RE.match(args.slug):
        print(f"--slug must be kebab-case, got {args.slug!r}", file=sys.stderr)
        return 2
    return archive(args.slug, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
