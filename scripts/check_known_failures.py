#!/usr/bin/env python3
"""Governs every test that is allowed to fail, so CI's red means something.

Why this exists
---------------
On 2026-08-04 the trunk itself was red: 2 backend tests, 18 jest tests and 1
Playwright test failed on ``staging`` with no branch responsible. Because every
PR inherited that red, "CI failed" carried no information, and merging over it
became routine — including that day's two promotions. A gate everyone has
learned to ignore is not a gate.

The fix is not to delete the failing tests. It is to make each one an explicit,
*executing*, expiring exception, so the suites go green and the next red is
genuinely new. The marker lives next to the test — an external list of test ids
drifts the moment a test is renamed.

Recognised markers
------------------
``@pytest.mark.xfail`` · ``it.failing`` / ``test.failing`` · ``test.fail()`` ·
``test.fixme``. Each must be classified by a nearby annotation:

``KNOWN-FAIL owner=<who> expires=<YYYY-MM-DD> -- <why>``
    A temporary quarantine. Fails this check once it expires, which is the
    forcing function: the exception has to be renewed with a reason or fixed.

``KNOWN_BYPASS:``
    A permanent, documented architectural gap kept visible in test reports
    (the pre-existing convention in ``common/tests/test_sensitive_fields.py``).
    No expiry — it is not waiting on anyone.

Use ``strict=True`` (pytest) or the executing forms (``it.failing``,
``test.fail``) wherever possible: they fail the build when the test starts
passing, so a fixed test cannot quietly stay quarantined.

The legacy budget
-----------------
The 2026-08-01 bulk e2e quarantine left ~347 un-annotated ``test.fixme`` calls.
Annotating them all now would bury this change, so they are counted instead:
the count may shrink freely but may not grow. A NEW quarantine has to carry an
annotation.

The placeholder-owner budget
-----------------------------
``owner=unassigned`` satisfies the annotation regex, so it never fails as
"unclassified" — but it names nobody to renew or chase the expiry. Counted the
same way as the legacy fixme budget: may shrink, may not grow. Give a new
quarantine a real owner instead of this placeholder.

Usage
-----
    python3 scripts/check_known_failures.py                 # expiry warns
    python3 scripts/check_known_failures.py --expiry-mode fail   # nightly
    python3 scripts/check_known_failures.py --inventory     # just list them
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories scanned, and the extensions that matter in each.
# Override with KNOWN_FAIL_ROOTS="backend/apps:.py,frontend/src:.ts:.tsx".
_DEFAULT_ROOTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("backend", (".py",)),
    ("frontend/src", (".ts", ".tsx")),
    ("frontend/e2e", (".ts", ".tsx")),
    ("test", (".dart",)),
    ("integration_test", (".dart",)),
)


def _roots() -> tuple[tuple[str, tuple[str, ...]], ...]:
    raw = os.environ.get("KNOWN_FAIL_ROOTS")
    if not raw:
        return _DEFAULT_ROOTS
    out = []
    for spec in raw.split(","):
        head, *exts = spec.strip().split(":")
        out.append((head, tuple(exts or (".py",))))
    return tuple(out)


SCAN_ROOTS = _roots()

PY_MARKER = re.compile(r"@pytest\.mark\.xfail\b")
JS_MARKER = re.compile(r"\b(?:it|test)\.(failing|fail|fixme)\b")

ANNOTATION = re.compile(
    r"KNOWN-FAIL\s+owner=(?P<owner>\S+)\s+expires=(?P<expires>\d{4}-\d{2}-\d{2})"
)
PERMANENT = "KNOWN_BYPASS"

# How far to look around a marker for its annotation. Python decorators put the
# reason inside the call; JS puts it in a comment above the enclosing test().
PY_LOOKAHEAD = 20
JS_LOOKBEHIND = 10

# Un-annotated ``test.fixme`` calls inherited from a bulk quarantine that
# predates this policy. A fresh repo starts at 0. If you adopt this gate on an
# existing codebase, set it to today's count once, then only ever lower it.
LEGACY_FIXME_BUDGET = int(os.environ.get("LEGACY_FIXME_BUDGET", "0"))

# KNOWN-FAIL markers carrying the literal placeholder ``owner=unassigned``
# satisfy the annotation regex (so they don't fail as "unclassified") but name
# nobody to renew or chase the expiry. Same shrink-only ratchet as the legacy
# fixme budget: lower this as markers get a real owner; never raise it.
PLACEHOLDER_OWNER_BUDGET = int(os.environ.get("PLACEHOLDER_OWNER_BUDGET", "0"))


@dataclass(frozen=True)
class Marker:
    """One test that is allowed to fail, and the terms it is allowed on."""

    path: str
    line: int
    kind: str
    owner: str | None = None
    expires: dt.date | None = None
    permanent: bool = False

    @property
    def location(self) -> str:
        return f"{self.path}:{self.line}"


def _annotation_of(window: str) -> tuple[str | None, dt.date | None, bool]:
    """Classify a marker from the text surrounding it."""
    if PERMANENT in window:
        return None, None, True
    match = ANNOTATION.search(window)
    if match is None:
        return None, None, False
    return match["owner"], dt.date.fromisoformat(match["expires"]), False


def _scan_python(rel_path: str, lines: list[str]) -> list[Marker]:
    markers: list[Marker] = []
    for index, line in enumerate(lines):
        if not PY_MARKER.search(line):
            continue
        window = "\n".join(lines[index : index + PY_LOOKAHEAD])
        owner, expires, permanent = _annotation_of(window)
        markers.append(
            Marker(rel_path, index + 1, "xfail", owner, expires, permanent)
        )
    return markers


def _is_comment(line: str) -> bool:
    """A marker named inside a comment is prose about the policy, not a marker."""
    stripped = line.lstrip()
    return stripped.startswith(("//", "*", "/*"))


def _scan_js(rel_path: str, lines: list[str]) -> list[Marker]:
    markers: list[Marker] = []
    for index, line in enumerate(lines):
        match = JS_MARKER.search(line)
        if match is None or _is_comment(line):
            continue
        start = max(0, index - JS_LOOKBEHIND)
        window = "\n".join(lines[start : index + 1])
        owner, expires, permanent = _annotation_of(window)
        markers.append(
            Marker(rel_path, index + 1, match.group(1), owner, expires, permanent)
        )
    return markers


def collect_markers(root: Path = REPO_ROOT) -> list[Marker]:
    """Every allowed-to-fail marker in the repository, in path order."""
    markers: list[Marker] = []
    for rel_root, suffixes in SCAN_ROOTS:
        base = root / rel_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in suffixes or not path.is_file():
                continue
            rel_path = str(path.relative_to(root))
            lines = path.read_text(encoding="utf-8").splitlines()
            scan = _scan_python if path.suffix == ".py" else _scan_js
            markers.extend(scan(rel_path, lines))
    return markers


def _legacy_problems(unannotated: list[Marker]) -> list[str]:
    """The legacy fixme budget may shrink, never grow."""
    count = len(unannotated)
    if count > LEGACY_FIXME_BUDGET:
        excess = count - LEGACY_FIXME_BUDGET
        listing = "\n".join(f"      {m.location}" for m in unannotated[-excess:])
        return [
            f"{excess} new un-annotated test.fixme call(s) — the legacy budget is "
            f"{LEGACY_FIXME_BUDGET}, found {count}. A new quarantine must carry\n"
            "      KNOWN-FAIL owner=<who> expires=<YYYY-MM-DD> -- <why>\n"
            "    Candidates (last in scan order, so likely yours):\n" + listing
        ]
    if count < LEGACY_FIXME_BUDGET:
        print(
            f"  note: only {count} legacy fixmes remain — lower "
            f"LEGACY_FIXME_BUDGET to {count} to hold the ground you took."
        )
    return []


def _placeholder_owner_problems(placeholder: list[Marker]) -> list[str]:
    """The owner=unassigned budget may shrink, never grow."""
    count = len(placeholder)
    if count > PLACEHOLDER_OWNER_BUDGET:
        excess = count - PLACEHOLDER_OWNER_BUDGET
        listing = "\n".join(f"      {m.location}" for m in placeholder[-excess:])
        return [
            f"{excess} new owner=unassigned quarantine(s) — the budget is "
            f"{PLACEHOLDER_OWNER_BUDGET}, found {count}. A new quarantine must\n"
            "      name a real owner: KNOWN-FAIL owner=<who> expires=<YYYY-MM-DD> -- <why>\n"
            "    Candidates (last in scan order, so likely yours):\n" + listing
        ]
    if count < PLACEHOLDER_OWNER_BUDGET:
        print(
            f"  note: only {count} owner=unassigned quarantines remain — lower "
            f"PLACEHOLDER_OWNER_BUDGET to {count} to hold the ground you took."
        )
    return []


def evaluate(
    markers: list[Marker], today: dt.date, expiry_mode: str
) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) for a set of markers."""
    failures: list[str] = []
    warnings: list[str] = []

    unclassified = [
        m for m in markers if not m.permanent and m.owner is None and m.kind != "fixme"
    ]
    for marker in unclassified:
        failures.append(
            f"{marker.location}: {marker.kind} with no classification. Add either\n"
            "      KNOWN-FAIL owner=<who> expires=<YYYY-MM-DD> -- <why>\n"
            "    for a temporary quarantine, or KNOWN_BYPASS: for a permanent,\n"
            "    documented architectural gap."
        )

    failures.extend(
        _legacy_problems([m for m in markers if m.kind == "fixme" and m.owner is None])
    )

    failures.extend(
        _placeholder_owner_problems([m for m in markers if m.owner == "unassigned"])
    )

    for marker in markers:
        if marker.expires is None or marker.expires >= today:
            continue
        overdue = (today - marker.expires).days
        message = (
            f"{marker.location}: quarantine expired {overdue} day(s) ago "
            f"(owner={marker.owner}). Fix the test, or renew the expiry with a "
            "reason it is still acceptable."
        )
        (failures if expiry_mode == "fail" else warnings).append(message)

    return failures, warnings


def _print_inventory(markers: list[Marker]) -> None:
    dated = sorted(
        (m for m in markers if m.expires is not None), key=lambda m: m.expires
    )
    permanent = [m for m in markers if m.permanent]
    legacy = [m for m in markers if m.kind == "fixme" and m.owner is None]
    placeholder = [m for m in markers if m.owner == "unassigned"]

    print(f"Expiring quarantines ({len(dated)}):")
    for marker in dated:
        print(f"  {marker.expires}  {marker.owner:<12} {marker.location}")
    print(f"Permanent documented gaps (KNOWN_BYPASS): {len(permanent)}")
    print(f"Legacy un-annotated test.fixme: {len(legacy)} (budget {LEGACY_FIXME_BUDGET})")
    print(
        f"Placeholder owner=unassigned quarantines: {len(placeholder)} "
        f"(budget {PLACEHOLDER_OWNER_BUDGET})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--expiry-mode",
        choices=("warn", "fail"),
        default="warn",
        help=(
            "What an expired quarantine does. 'warn' on PRs so an unrelated "
            "author is never blocked by a date rollover; 'fail' nightly, which "
            "is what actually forces the cleanup."
        ),
    )
    parser.add_argument(
        "--inventory", action="store_true", help="Print the inventory and exit 0."
    )
    parser.add_argument(
        "--today",
        default=None,
        help="Override today's date (YYYY-MM-DD) — for testing this script.",
    )
    args = parser.parse_args(argv)

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    markers = collect_markers()

    if args.inventory:
        _print_inventory(markers)
        return 0

    failures, warnings = evaluate(markers, today, args.expiry_mode)

    for warning in warnings:
        print(f"WARN  {warning}")
    for failure in failures:
        print(f"FAIL  {failure}")

    if failures:
        print(f"\nKnown-failure policy: {len(failures)} violation(s).")
        return 1

    _print_inventory(markers)
    print("\nKnown-failure policy: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
