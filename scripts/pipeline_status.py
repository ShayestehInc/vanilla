#!/usr/bin/env python3
"""Report pipeline position from ``tasks/pipeline-state.md`` -- with no model call.

Why this exists
---------------
The ``/status`` skill has always documented itself as "no AI needed", but it was
implemented as a prompt an opus-tier model executed: read two files, count some
checkboxes, print. That is the same narrate-instead-of-execute failure that let
20 oversized files through a passing Review stage -- a deterministic job dressed
up as a judgement call, and billed like one.

It also validates the state file. CLAUDE.md specifies ``Stage: [1-12 or
COMPLETE]``; the live file had drifted to ``Stage: IN PROGRESS`` and
``Tier: trivial + quick``, which meant the session-start rule "resume from saved
stage and tier" had nothing parseable to resume from. Auto-resume was silently
dead and nothing noticed, because nothing checked.

Usage
-----
    python scripts/pipeline_status.py            # print status, exit 1 if malformed
    python scripts/pipeline_status.py --check    # validate only, no output on success
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "tasks" / "pipeline-state.md"
BUILD_PLAN = REPO_ROOT / "BUILD_PLAN.md"

COMPLETE = "COMPLETE"

# Tier -> ordered stage names. The index in this list + 1 is the stage number,
# so the tier's length is also its total stage count.
TIER_STAGES: dict[str, list[str]] = {
    "trivial": ["Dev (inline, orchestrator self-review)"],
    "quick": ["Dev", "Review", "Fix"],
    "standard": ["PlanResearch", "UI Design", "Dev", "ReviewFix", "QA"],
    "full-cycle": [
        "Plan",
        "Research",
        "UI Design",
        "Dev",
        "Review",
        "Fix",
        "QA",
        "UX",
        "Security",
        "Arch",
        "Hacker",
        "Verify",
    ],
}

# Canonical stage artifacts, in pipeline order. These names are a contract:
# every skill reads these exact paths, so a ``dev-done-<suffix>.md`` variant
# makes a downstream stage read *a* summary rather than *the* one.
ARTIFACTS: list[tuple[str, str]] = [
    ("next-ticket.md", "Plan"),
    ("research-report.md", "Research"),
    ("ui-design.md", "UI Design"),
    ("dev-done.md", "Dev"),
    ("review-findings.md", "Review / ReviewFix"),
    ("qa-report.md", "QA"),
    ("ux-audit.md", "UX"),
    ("security-audit.md", "Security"),
    ("architecture-review.md", "Arch"),
    ("hacker-report.md", "Hacker"),
    ("ship-decision.md", "Verify"),
]

_FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z ]*?):\s*(.*)$")

# ``dev-done-backend.md``, ``review-findings-dialer-shared-pool.md`` and friends.
# A suffixed variant is invisible to the skills, which all read the bare
# canonical path -- so the stage downstream silently reads the wrong summary.
_VARIANT_RE = re.compile(
    "^(" + "|".join(re.escape(Path(n).stem) for n, _ in ARTIFACTS) + r")-.+\.md$"
)


@dataclass
class PipelineState:
    """Parsed ``pipeline-state.md``. ``errors`` non-empty means malformed."""

    task: str = ""
    tier: str = ""
    stage: str = ""
    agent: str = ""
    updated: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def total_stages(self) -> int:
        return len(TIER_STAGES.get(self.tier, []))

    @property
    def stage_name(self) -> str:
        if self.stage == COMPLETE:
            return COMPLETE
        stages = TIER_STAGES.get(self.tier, [])
        index = int(self.stage) - 1
        return stages[index] if 0 <= index < len(stages) else "?"


@dataclass
class PlanProgress:
    done: int = 0
    pending: int = 0
    next_task: str = ""

    @property
    def total(self) -> int:
        return self.done + self.pending

    @property
    def percent(self) -> int:
        return round(self.done * 100 / self.total) if self.total else 0


def _parse_fields(text: str) -> dict[str, str]:
    """Collect ``Key: value`` header lines, stopping at the Notes section."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.strip().startswith("Notes:"):
            break
        match = _FIELD_RE.match(line.strip())
        if match:
            fields[match.group(1).strip().lower()] = match.group(2).strip()
    return fields


def _validate(state: PipelineState) -> None:
    """Append a message to ``state.errors`` for every schema violation."""
    if state.tier not in TIER_STAGES:
        state.errors.append(
            f"Tier: {state.tier!r} is not one of {', '.join(TIER_STAGES)}"
        )
    if state.stage == COMPLETE:
        return
    if not state.stage.isdigit():
        state.errors.append(
            f"Stage: {state.stage!r} must be an integer or {COMPLETE} "
            "(CLAUDE.md: 'Stage: [1-12 or COMPLETE]')"
        )
        return
    total = state.total_stages
    if total and not 1 <= int(state.stage) <= total:
        state.errors.append(
            f"Stage: {state.stage} is outside 1..{total} for tier {state.tier!r}"
        )


def _check_artifact_names(errors: list[str], tasks_dir: Path) -> None:
    """Reject suffixed variants of a canonical stage artifact at tasks/ top level."""
    for entry in sorted(tasks_dir.glob("*.md")):
        match = _VARIANT_RE.match(entry.name)
        if match:
            errors.append(
                f"tasks/{entry.name} is a variant of the canonical artifact "
                f"tasks/{match.group(1)}.md. Every skill reads the bare canonical "
                f"path, so this file is invisible to the pipeline — write to "
                f"tasks/{match.group(1)}.md, or archive it."
            )


# Where a stray copy of a canonical artifact can hide. ``tasks/archive/`` is
# the intended home for a finished run's set, and these are not ours to walk.
_SKIP_DIRS = {
    ".git",
    ".next",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "coverage",
    "staticfiles",
}

_STATE_FILE_NAME = "pipeline-state.md"


def _check_stray_artifacts(errors: list[str], tasks_dir: Path) -> None:
    """Reject a canonical artifact name found outside the ``tasks/`` tree.

    ``frontend/tasks/pipeline-state.md`` held the real state of a run for five
    stages while this script validated the format of a different, completed
    task -- and exited 0, because it only ever looked at one path. A canonical
    name elsewhere in the repo is invisible to every skill, so it is an error
    wherever it sits.

    Inside ``tasks/`` the name is fine below the top level: ``archive/<slug>/``
    is where a finished run's set belongs and ``templates/`` holds the blank
    stage templates. Top-level suffixed variants are ``_check_artifact_names``.
    """
    canonical = {name for name, _ in ARTIFACTS} | {_STATE_FILE_NAME}
    for path in REPO_ROOT.rglob("*.md"):
        if path.name not in canonical:
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if tasks_dir == path.parent or tasks_dir in path.parents:
            continue
        errors.append(
            f"{path.relative_to(REPO_ROOT)} uses the canonical artifact name "
            f"{path.name}, but every skill reads tasks/{path.name}. Move it "
            f"to tasks/{path.name}, archive it under tasks/archive/<slug>/, "
            "or rename it."
        )


def read_state(path: Path = STATE_FILE) -> PipelineState:
    if not path.exists():
        return PipelineState(errors=[f"{path} does not exist"])
    fields = _parse_fields(path.read_text(encoding="utf-8"))
    state = PipelineState(
        task=fields.get("task", ""),
        tier=fields.get("tier", ""),
        stage=fields.get("stage", ""),
        agent=fields.get("agent", ""),
        updated=fields.get("last updated", ""),
    )
    for name, value in (("Task", state.task), ("Stage", state.stage)):
        if not value:
            state.errors.append(f"{name}: field is missing or empty")
    _validate(state)
    _check_artifact_names(state.errors, path.parent)
    _check_stray_artifacts(state.errors, path.parent)
    return state


def read_plan(path: Path = BUILD_PLAN) -> PlanProgress:
    if not path.exists():
        return PlanProgress()
    progress = PlanProgress()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- [x]"):
            progress.done += 1
        elif line.startswith("- [ ]"):
            progress.pending += 1
            if not progress.next_task:
                progress.next_task = line[5:].strip()
    return progress


def _render(state: PipelineState, progress: PlanProgress) -> str:
    stage = (
        COMPLETE
        if state.stage == COMPLETE
        else f"{state.stage} / {state.total_stages} — {state.stage_name}"
    )
    lines = [
        "Pipeline Status",
        "===============",
        f"Task:    {state.task}",
        f"Tier:    {state.tier} ({state.total_stages} stages)",
        f"Stage:   {stage}",
        f"Agent:   {state.agent}",
        f"Updated: {state.updated}",
        "",
        "Build Plan Progress",
        "===================",
        f"Completed: {progress.done} / {progress.total} tasks ({progress.percent}%)",
        f"Next task: {progress.next_task or '—'}",
        "",
        "Stage Artifacts",
        "===============",
    ]
    tasks_dir = REPO_ROOT / "tasks"
    for name, stage_label in ARTIFACTS:
        mark = "x" if (tasks_dir / name).exists() else " "
        lines.append(f"[{mark}] tasks/{name:<24} ({stage_label})")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the state file only; print nothing when it is well-formed",
    )
    args = parser.parse_args()

    state = read_state()
    if state.errors:
        print(f"{STATE_FILE.relative_to(REPO_ROOT)} is malformed:", file=sys.stderr)
        for error in state.errors:
            print(f"  - {error}", file=sys.stderr)
        print(
            "\nCLAUDE.md defines the schema. A malformed state file silently "
            "breaks the session-start 'resume from saved stage' rule.",
            file=sys.stderr,
        )
        return 1
    if not args.check:
        print(_render(state, read_plan()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
