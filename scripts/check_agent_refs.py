#!/usr/bin/env python3
"""Fail when anything names a Claude agent that does not exist.

Why this exists
---------------
When duplicated agent files are merged or renamed, the skills are the obvious
place to update and the easy place to stop. In the project this boilerplate
came from, a consolidation left five *other* live files pointing at deleted
agent paths -- a backend docstring that cited an agent file as the source of an
enum's vocabulary, a staged ticket telling its implementer to go read the file,
and three planning documents. Two manual review passes to find them all.

Same lesson as ``check_code_size.py`` and ``check_known_failures.py``: a rule
nobody measures is a rule nobody follows. This is the mechanical half of
"leave no dangling agent reference".

What it checks
--------------
1. Every ``.claude/agents/*.md`` declares a ``name:`` matching its filename,
   and every ``.claude/skills/*/SKILL.md`` a ``name:`` matching its directory.
   A mismatch makes the agent or skill unreachable by the name people type.
2. Every ``subagent_type="X"`` in a tracked file resolves to a real agent.
3. Every ``.claude/agents/<name>.md`` path reference resolves to a real file.

Deliberately NOT checked: bare prose mentions of an agent name with no path and
no ``subagent_type=`` (too many false positives in tickets), and anything under
the history paths below -- an archived report should say what was true when it
was written, not what is true now.

Usage:
    python3 scripts/check_agent_refs.py
    python3 scripts/check_agent_refs.py --list    # print the inventory, exit 0

Put ``agent-ref-ok`` in a line to exempt it, e.g. a deliberate historical note.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = REPO_ROOT / ".claude" / "agents"
SKILL_DIR = REPO_ROOT / ".claude" / "skills"

# History: these say what was true when written, and are never rewritten.
HISTORY_PREFIXES = (
    "tasks/archive/",
    "docs/project-artifact/entries/",
    ".claude/worktrees/",
)
EXEMPT_MARKER = "agent-ref-ok"
TEXT_SUFFIXES = {".md", ".py", ".sh", ".ts", ".tsx", ".js", ".jsx", ".json", ".yml", ".yaml"}

SUBAGENT_RE = re.compile(r'subagent_type\s*=\s*"([a-zA-Z0-9_-]+)"')
AGENT_PATH_RE = re.compile(r"\.claude/agents/([a-zA-Z0-9_-]+)\.md")
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.M)


def frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    match = NAME_RE.search(parts[1])
    return match.group(1).strip().strip("\"'") if match else None


def frontmatter_errors() -> list[str]:
    """A declared name that differs from the path makes the thing unreachable."""
    errors: list[str] = []
    for path in sorted(AGENT_DIR.glob("*.md")):
        declared = frontmatter_name(path)
        rel = path.relative_to(REPO_ROOT)
        if declared is None:
            errors.append(f"{rel}: no `name:` in frontmatter")
        elif declared != path.stem:
            errors.append(f"{rel}: frontmatter name `{declared}` != filename `{path.stem}`")
    for path in sorted(SKILL_DIR.glob("*/SKILL.md")):
        declared = frontmatter_name(path)
        rel, directory = path.relative_to(REPO_ROOT), path.parent.name
        if declared is None:
            errors.append(f"{rel}: no `name:` in frontmatter")
        elif declared != directory:
            errors.append(
                f"{rel}: frontmatter name `{declared}` != directory `{directory}` "
                "-- the skill is unreachable by that name"
            )
    return errors


def tracked_text_files() -> list[str]:
    listing = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    return [
        rel for rel in listing
        if not rel.startswith(HISTORY_PREFIXES) and Path(rel).suffix in TEXT_SUFFIXES
    ]


def reference_errors(agents: set[str]) -> list[str]:
    errors: list[str] = []
    for rel in tracked_text_files():
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for lineno, line in enumerate(lines, 1):
            if EXEMPT_MARKER in line:
                continue
            for name in SUBAGENT_RE.findall(line):
                if name not in agents:
                    errors.append(f'{rel}:{lineno}: subagent_type="{name}" is not an agent')
            for name in AGENT_PATH_RE.findall(line):
                if name not in agents:
                    errors.append(f"{rel}:{lineno}: .claude/agents/{name}.md does not exist")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="print the inventory and exit 0")
    args = parser.parse_args()

    agents = {p.stem for p in AGENT_DIR.glob("*.md")}
    skills = {p.parent.name for p in SKILL_DIR.glob("*/SKILL.md")}

    if args.list:
        print(f"agents ({len(agents)}): {' '.join(sorted(agents))}")
        print(f"skills ({len(skills)}): {' '.join(sorted(skills))}")
        return 0

    errors = frontmatter_errors() + reference_errors(agents)
    if errors:
        print(f"Agent-reference gate: {len(errors)} problem(s)\n")
        for err in errors:
            print(f"  {err}")
        print(
            "\nEvery agent named anywhere must exist. If a reference is a deliberate\n"
            "historical note, put `agent-ref-ok` in that line."
        )
        return 1

    print(f"Agent-reference gate: clean ({len(agents)} agents, {len(skills)} skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
