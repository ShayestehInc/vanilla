#!/usr/bin/env python3
"""Enforce the CLAUDE.md Clean Code size rules on changed code.

Why this exists
---------------
CLAUDE.md has said "no new file over ~400 lines" and "functions <= 30 lines,
never add to a function already over 50" since the July 2026 clean-code
effort. Nothing enforced it. In the five days to 2026-07-26, **20 new files
shipped over 400 lines** -- every one of them through a passing Review stage,
because a reviewing agent can narrate compliance with a rule it isn't
measured against. A rule nobody measures is a suggestion.

What it checks
--------------
Only code the current branch actually adds or touches, measured against
``git merge-base <trunk> HEAD`` (trunk = ``$CODE_SIZE_BASE_REF``, else origin/main, else origin/master) (not ``HEAD~1`` -- a squashed feature
branch would otherwise report every file as new).

1. **Added file over the line cap** -- hard failure. Applies to source and
   tests alike: the 1,717-line test file this rule was written in response to
   is exactly the case a tests-exempt gate would wave through.
2. **Added Python file containing a function over the function cap** -- hard
   failure. A new file has no excuse for arriving with a god function.
3. **Modified Python file where a function the diff touches is over the
   function cap** -- hard failure. This is the "never add to a function
   already over 50" rule: pre-existing long functions are grandfathered until
   someone edits them.

Deliberately not checked: function length in TypeScript. Doing it properly
needs a real TS parser, and a brittle regex approximation that cries wolf
would get the whole gate disabled within a week. File size covers TS; the
function rule is Python-only and this limitation is intentional.

Waivers
-------
A commit that genuinely needs an exemption puts a line in its message:

    size-waiver: <path or glob> -- <reason>

The reason is required and recorded in the log, so a waiver is a decision
someone made on purpose rather than a silent bypass.

Usage
-----
    python scripts/check_code_size.py                 # vs the trunk merge-base
    python scripts/check_code_size.py --base <ref>
    python scripts/check_code_size.py --list           # report, never fail
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAX_FILE_LINES = 400
MAX_FUNCTION_LINES = 50

# Paths that are generated, vendored, or otherwise not hand-authored.
EXEMPT_GLOBS: tuple[str, ...] = (
    "*/migrations/*",
    "*/generated/*",
    "*.g.dart",
    "*.freezed.dart",
    "*.snap",
    "*/__pycache__/*",
    "scripts/seed*.py",
)

CHECKED_SUFFIXES: tuple[str, ...] = (".py", ".ts", ".tsx", ".dart", ".kt", ".swift", ".go", ".rb")

WAIVER_RE = re.compile(r"^\s*size-waiver:\s*(?P<path>\S+)\s*--\s*(?P<reason>.+)$")


@dataclass
class Violation:
    path: str
    kind: str
    detail: str
    measured: int
    cap: int

    def render(self) -> str:
        return (
            f"  {self.path}\n"
            f"      {self.kind}: {self.detail} "
            f"({self.measured} lines, cap {self.cap})"
        )


@dataclass
class Waiver:
    pattern: str
    reason: str


@dataclass
class Report:
    violations: list[Violation] = field(default_factory=list)
    waived: list[tuple[Violation, Waiver]] = field(default_factory=list)


def _git(*args: str) -> str:
    """Run a git command from the repo root and return stdout."""
    return subprocess.run(
        ("git", *args),
        capture_output=True,
        text=True,
        check=True,
        cwd=_repo_root(),
    ).stdout.strip()


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_base(explicit: str | None) -> str:
    """The merge-base to diff against, falling back sanely on a shallow clone."""
    if explicit:
        return explicit
    env_base = os.environ.get("CODE_SIZE_BASE_REF")
    candidates = (env_base,) if env_base else ("origin/main", "main", "origin/master", "master")
    for ref in candidates:
        try:
            return _git("merge-base", ref, "HEAD")
        except subprocess.CalledProcessError:
            continue
    # Shallow CI checkout with no master: fall back to the first parent so the
    # gate still says something rather than crashing the build.
    return _git("rev-parse", "HEAD^")


def changed_files(base: str) -> tuple[list[str], list[str]]:
    """(added, modified) paths in scope, relative to the repo root."""
    raw = _git("diff", "--name-status", "--diff-filter=AM", f"{base}...HEAD")
    added: list[str] = []
    modified: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        status, _, path = line.partition("\t")
        path = path.strip()
        if not _in_scope(path):
            continue
        (added if status.startswith("A") else modified).append(path)
    return added, modified


def _in_scope(path: str) -> bool:
    if not path.endswith(CHECKED_SUFFIXES):
        return False
    return not any(fnmatch.fnmatch(path, glob) for glob in EXEMPT_GLOBS)


def parse_waivers(base: str) -> list[Waiver]:
    """Waivers declared in any commit message on this branch."""
    log = _git("log", "--format=%B", f"{base}..HEAD")
    waivers: list[Waiver] = []
    for line in log.splitlines():
        match = WAIVER_RE.match(line)
        if match:
            waivers.append(
                Waiver(
                    pattern=match.group("path"),
                    reason=match.group("reason").strip(),
                )
            )
    return waivers


def _line_count(path: Path) -> int:
    with path.open(encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def _function_records(tree: ast.AST) -> list[tuple[str, int, int, int]]:
    """Return functions keyed by lexical path, not their ambiguous bare name."""
    records: list[tuple[str, int, int, int]] = []

    class FunctionVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scope: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def _visit_function(
            self, node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> None:
            end = node.end_lineno or node.lineno
            name = ".".join([*self.scope, node.name])
            records.append((name, node.lineno, end, end - node.lineno + 1))
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        visit_FunctionDef = _visit_function
        visit_AsyncFunctionDef = _visit_function

    FunctionVisitor().visit(tree)
    return records


def _long_functions(path: Path) -> list[tuple[str, int, int, int]]:
    """(qualified name, start, end, length) for functions over the cap."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        # A file that doesn't parse is the type checker's problem, not ours.
        return []
    return [
        record
        for record in _function_records(tree)
        if record[3] > MAX_FUNCTION_LINES
    ]


def _touched_lines(base: str, path: str) -> set[int]:
    """Line numbers in the post-image that the diff adds or changes."""
    diff = _git("diff", "-U0", f"{base}...HEAD", "--", path)
    touched: set[int] = set()
    for line in diff.splitlines():
        if not line.startswith("@@"):
            continue
        match = re.search(r"\+(\d+)(?:,(\d+))?", line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or 1)
        touched.update(range(start, start + count))
    return touched


def _violations_for_added(path: str, full: Path) -> list[Violation]:
    """A brand-new file must be under the cap and free of god functions."""
    found: list[Violation] = []
    lines = _line_count(full)
    if lines > MAX_FILE_LINES:
        found.append(
            Violation(
                path=path,
                kind="new file over the line cap",
                detail="split it before it becomes a god file",
                measured=lines,
                cap=MAX_FILE_LINES,
            )
        )
    if path.endswith(".py"):
        found.extend(
            Violation(
                path=f"{path}:{start}",
                kind="new function over the line cap",
                detail=f"{name}()",
                measured=length,
                cap=MAX_FUNCTION_LINES,
            )
            for name, start, _end, length in _long_functions(full)
        )
    return found


def _function_lengths_at(base: str, path: str) -> dict[str, int]:
    """``{qualified_name: length}`` for every function at ``base``.

    Returns empty when the file is new or unparseable there — callers treat a
    missing baseline as "no previous length to compare against".
    """
    try:
        source = _git("show", f"{base}:{path}")
    except subprocess.CalledProcessError:
        return {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    return {
        name: length
        for name, _start, _end, length in _function_records(tree)
    }


def _violations_for_modified(base: str, path: str, full: Path) -> list[Violation]:
    """Long functions this branch actually made longer.

    Two exemptions, both deliberate:

    * **Untouched** long functions are grandfathered — the rule is "never *add*
      to a function already over the cap", not "never open a file containing
      one".
    * A touched long function that did **not grow** is fine. Deleting a stale
      comment, or refactoring 103 lines down to 60, adds nothing; failing those
      would mean the gate punishes exactly the cleanup it exists to encourage,
      and the first thing people do to a gate like that is switch it off.
    """
    if not path.endswith(".py"):
        return []
    long_funcs = _long_functions(full)
    if not long_funcs:
        return []
    touched = _touched_lines(base, path)
    was = _function_lengths_at(base, path)

    violations: list[Violation] = []
    for name, start, end, length in long_funcs:
        if not touched & set(range(start, end + 1)):
            continue
        before = was.get(name)
        if before is not None and length <= before:
            continue  # touched, but no longer than it already was
        grew_from = "" if before is None else f" (was {before})"
        violations.append(
            Violation(
                path=f"{path}:{start}",
                kind="grew a function that is already over the line cap",
                detail=f"{name}(){grew_from} -- extract before adding to it",
                measured=length,
                cap=MAX_FUNCTION_LINES,
            )
        )
    return violations


def collect(base: str) -> Report:
    root = _repo_root()
    added, modified = changed_files(base)
    report = Report()
    waivers = parse_waivers(base)

    def record(violation: Violation) -> None:
        # Function-level violations carry a ``:line`` suffix, so match the bare
        # file path too — otherwise a perfectly good file-path waiver silently
        # never applies, which is how the first real waiver failed to take.
        candidates = {violation.path, violation.path.rsplit(":", 1)[0]}
        for waiver in waivers:
            if any(fnmatch.fnmatch(c, waiver.pattern) for c in candidates):
                report.waived.append((violation, waiver))
                return
        report.violations.append(violation)

    for path in added:
        full = root / path
        if full.exists():
            for violation in _violations_for_added(path, full):
                record(violation)

    for path in modified:
        full = root / path
        if full.exists():
            for violation in _violations_for_modified(base, path, full):
                record(violation)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="ref to diff against (default: merge-base)")
    parser.add_argument(
        "--list",
        action="store_true",
        help="report findings but always exit 0",
    )
    args = parser.parse_args()

    base = resolve_base(args.base)
    report = collect(base)

    for violation, waiver in report.waived:
        print(f"WAIVED  {violation.path} -- {waiver.reason}")

    if not report.violations:
        print(f"Clean Code size gate: OK (base {base[:12]})")
        return 0

    print(
        f"\nClean Code size gate: {len(report.violations)} violation(s) "
        f"(base {base[:12]})\n"
    )
    for violation in report.violations:
        print(violation.render())
    print(
        "\nCaps: files <= "
        f"{MAX_FILE_LINES} lines, functions <= {MAX_FUNCTION_LINES} lines "
        "(CLAUDE.md > Clean Code Rules).\n"
        "Split the file or extract the function. If an exemption is genuinely\n"
        "right, add a line to the commit message:\n"
        "    size-waiver: <path or glob> -- <why>\n"
    )
    return 0 if args.list else 1


if __name__ == "__main__":
    sys.exit(main())
