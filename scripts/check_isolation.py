#!/usr/bin/env python3
"""Fail the build when a viewset over tenant-scoped data has no tenant isolation.

Why this exists
---------------
CLAUDE.md's first Key Warning is "Never bypass tenant isolation -- unscoped
queries = data leak", and `ultrareview` asks "IDOR: can user A access user B's
data?" as a prose checkbox an agent ticks about its own work. In July 2026 two
real isolation bugs shipped anyway; both were caught only because a human
happened to route the change to an independent review. A rule nobody measures is
a suggestion -- the same lesson `scripts/check_code_size.py` was written for, and
this script deliberately copies its architecture.

What it checks
--------------
Exactly one rule, chosen because it can be decided correctly from the AST:

    A ModelViewSet-family class over a tenant-scoped model, with neither
    the isolation mixin in its bases nor a `get_queryset` override, is
    unscoped: it would serve every tenant's rows to every request.

The model is read from `queryset = Lead.objects...` or from the django-stubs
generic parameter (`ModelViewSet[Message]`); in the codebase this was written
for, all but one ModelViewSet-family class resolved a model one of those two ways. A model counts as
tenant-scoped when it inherits a scoped base model, or
declares the tenant ForeignKey. A viewset counts as isolated when it composes
the isolation mixin directly or inherits a project class that does, resolved
to a fixpoint across the backend.

Deliberately NOT checked, and you should know the holes:

- **`get_queryset` overrides.** Plenty of viewsets scope by hand. Whether that
  scoping is *correct* is not decidable from the AST -- the real-world scoping bug this gate was written after was
  a wrong `get_queryset`, not a missing one. This gate defers to the override and
  catches only what it can decide with certainty. Reviewing override bodies
  remains a human/agent job; this script does not make Review redundant, it makes
  the mechanical half mechanical.
- Actor-scope composition order, pagination, dict-returning services, and
  plain `viewsets.ViewSet` classes with no model.

Each of those needs information the AST doesn't carry, and a gate that cries wolf
gets disabled within a week -- at which point it protects nothing. One correct
check beats three approximate ones.

Scope
-----
Only what the branch adds or touches, against `git merge-base origin/master
HEAD`. Pre-existing viewsets are grandfathered until someone edits them, so the
gate can land green on a codebase with 57 viewsets already in it.

Waivers
-------
A genuine exemption goes in the commit message, reason required:

    isolation-waiver: <path or glob> -- <reason>

Usage
-----
    python scripts/check_isolation.py
    python scripts/check_isolation.py --base <ref>
    python scripts/check_isolation.py --all      # report every viewset, never fail
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Reuse the git plumbing that already backs the size gate rather than growing a
# second, subtly different implementation of "what did this branch touch".
from check_code_size import (  # noqa: E402
    _git,
    _repo_root,
    _touched_lines,
    resolve_base,
)

# --- project configuration -------------------------------------------------
# Override any of these with an env var so the gate follows your naming without
# a fork. See docs/stacks/django-next.md.
BACKEND = os.environ.get("ISOLATION_ROOT", "backend/")
ISOLATION_MIXIN = os.environ.get("ISOLATION_MIXIN", "TenantIsolationMixin")
ACTOR_MIXIN = os.environ.get("ISOLATION_ACTOR_MIXIN", "ActorScopeMixin")
TENANT_FK = os.environ.get("ISOLATION_TENANT_FK", "tenant")
SCOPED_BASES = frozenset(
    os.environ.get("ISOLATION_SCOPED_BASES", "TenantScopedModel,WorkspaceScopedModel").split(",")
)
# ---------------------------------------------------------------------------
VIEWSET_MARKERS = ("ModelViewSet", "ReadOnlyModelViewSet")

EXEMPT_GLOBS: tuple[str, ...] = ("*/migrations/*", "*/tests/*", "*/test_*.py")

WAIVER_RE = re.compile(r"^\s*isolation-waiver:\s*(?P<path>\S+)\s*--\s*(?P<reason>.+)$")


@dataclass
class Violation:
    path: str
    line: int
    viewset: str
    model: str

    def render(self) -> str:
        return (
            f"  {self.path}:{self.line}\n"
            f"      {self.viewset} serves {self.model}, which is tenant-scoped, "
            f"but does not compose {ISOLATION_MIXIN}.\n"
            f"      Every request would see every client's rows. See CLAUDE.md "
            f"> Data Isolation."
        )


@dataclass
class Codebase:
    """Facts gathered once from the whole backend, not just the diff."""

    client_scoped_models: set[str] = field(default_factory=set)
    isolated_viewsets: set[str] = field(default_factory=set)


def _backend_files() -> list[Path]:
    root = _repo_root()
    return [
        root / path
        for path in _git("ls-files", f"{BACKEND}*.py").splitlines()
        if path and not _is_exempt(path)
    ]


def _is_exempt(path: str) -> bool:
    return any(fnmatch.fnmatch(path, glob) for glob in EXEMPT_GLOBS)


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        # A file that won't parse is the type checker's problem, not ours.
        return None


def _base_names(node: ast.ClassDef) -> list[str]:
    """Declared base names, flattened: `viewsets.ViewSet` -> `ViewSet`,
    `ModelViewSet[Lead]` -> `ModelViewSet`."""
    names: list[str] = []
    for base in node.bases:
        target = base.value if isinstance(base, ast.Subscript) else base
        if isinstance(target, ast.Attribute):
            names.append(target.attr)
        elif isinstance(target, ast.Name):
            names.append(target.id)
    return names


def _declares_client_fk(node: ast.ClassDef) -> bool:
    for stmt in node.body:
        targets = stmt.targets if isinstance(stmt, ast.Assign) else []
        if isinstance(stmt, ast.AnnAssign):
            targets = [stmt.target]
        for target in targets:
            if isinstance(target, ast.Name) and target.id == TENANT_FK:
                return True
    return False


def _queryset_model(node: ast.ClassDef) -> str | None:
    """`queryset = Lead.objects.select_related(...)` -> `Lead`."""
    for stmt in node.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "queryset" for t in stmt.targets
        ):
            continue
        for sub in ast.walk(stmt.value):
            if isinstance(sub, ast.Attribute) and sub.attr == "objects":
                if isinstance(sub.value, ast.Name):
                    return sub.value.id
    return None


def _resolve_fixpoint(direct: set[str], edges: dict[str, list[str]]) -> set[str]:
    """Grow `direct` with any class inheriting something already in the set."""
    resolved = set(direct)
    changed = True
    while changed:
        changed = False
        for child, parents in edges.items():
            if child not in resolved and any(p in resolved for p in parents):
                resolved.add(child)
                changed = True
    return resolved


def scan_codebase() -> Codebase:
    """One pass over every backend module, building both fact sets."""
    model_direct: set[str] = set()
    viewset_direct: set[str] = set()
    edges: dict[str, list[str]] = {}

    for path in _backend_files():
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = _base_names(node)
            edges[node.name] = bases
            if SCOPED_BASES.intersection(bases) or _declares_client_fk(node):
                model_direct.add(node.name)
            if ISOLATION_MIXIN in bases:
                viewset_direct.add(node.name)

    return Codebase(
        client_scoped_models=_resolve_fixpoint(model_direct, edges),
        isolated_viewsets=_resolve_fixpoint(viewset_direct, edges),
    )


def _viewset_violations(
    path: str, tree: ast.Module, facts: Codebase, touched: set[int] | None
) -> list[Violation]:
    """Unisolated viewsets in one file. `touched=None` means the file is new."""
    found: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = _base_names(node)
        if not any(marker in base for base in bases for marker in VIEWSET_MARKERS):
            continue
        if node.name in facts.isolated_viewsets:
            continue
        model = _queryset_model(node)
        if model is None or model not in facts.client_scoped_models:
            continue
        end = node.end_lineno or node.lineno
        if touched is not None and not touched.intersection(range(node.lineno, end + 1)):
            continue  # pre-existing and untouched by this branch
        found.append(Violation(path, node.lineno, node.name, model))
    return found


def _changed_backend_files(base: str) -> list[tuple[str, bool]]:
    """(path, is_new) for backend Python the branch adds or modifies."""
    raw = _git("diff", "--name-status", "--diff-filter=AM", f"{base}...HEAD")
    files: list[tuple[str, bool]] = []
    for line in raw.splitlines():
        status, _, path = line.partition("\t")
        path = path.strip()
        if path.startswith(BACKEND) and path.endswith(".py") and not _is_exempt(path):
            files.append((path, status.startswith("A")))
    return files


def _waived(path: str, base: str) -> str | None:
    log = _git("log", "--format=%B", f"{base}..HEAD")
    for line in log.splitlines():
        match = WAIVER_RE.match(line)
        if match and fnmatch.fnmatch(path, match.group("path")):
            return match.group("reason").strip()
    return None


def collect(base: str, scan_all: bool) -> list[Violation]:
    facts = scan_codebase()
    root = _repo_root()
    violations: list[Violation] = []

    if scan_all:
        for path in _backend_files():
            tree = _parse(path)
            if tree is not None:
                relative = str(path.relative_to(root))
                violations += _viewset_violations(relative, tree, facts, None)
        return violations

    for path, is_new in _changed_backend_files(base):
        tree = _parse(root / path)
        if tree is None:
            continue
        touched = None if is_new else _touched_lines(base, path)
        violations += _viewset_violations(path, tree, facts, touched)
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="ref to diff against (default: merge-base)")
    parser.add_argument(
        "--all",
        action="store_true",
        help="report every unisolated viewset in the backend; always exits 0",
    )
    args = parser.parse_args()

    base = resolve_base(args.base)
    violations = collect(base, args.all)

    if args.all:
        print(f"Isolation gate: {len(violations)} unisolated viewset(s) repo-wide")
        for violation in violations:
            print(violation.render())
        return 0

    live = [v for v in violations if _waived(v.path, base) is None]
    for violation in violations:
        reason = _waived(violation.path, base)
        if reason:
            print(f"WAIVED {violation.path}: {violation.viewset} -- {reason}")

    if not live:
        print(f"Isolation gate: clean (base {base[:12]})")
        return 0

    print(f"Isolation gate: {len(live)} violation(s) (base {base[:12]})\n")
    for violation in live:
        print(violation.render())
    print(
        f"\nCompose {ISOLATION_MIXIN} on the viewset. For restricted-persona "
        f"viewsets add\n{ACTOR_MIXIN} *before* it, so the actor filter narrows "
        "last.\nIf an exemption is genuinely right, add to the commit message:\n"
        "    isolation-waiver: <path or glob> -- <why>"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
