---
name: status
description: "Show pipeline progress instantly by running scripts/pipeline_status.py. Deterministic — no model reasoning, no file reading, no tokens spent counting checkboxes."
---

# Pipeline Status

Run exactly this, and show the output:

```bash
python scripts/pipeline_status.py
```

That is the whole skill. Do not read `tasks/pipeline-state.md` or `BUILD_PLAN.md`
yourself, do not re-format the output, and do not launch an agent.

## Why it's a script

This skill always claimed "no AI needed", but it was written as a prompt an
opus-tier model executed: read two files, count checkboxes, print a table. That
is a deterministic job billed as a judgement call — the same
narrate-instead-of-execute pattern that let 20 oversized files through a passing
Review stage. Now the deterministic part is deterministic.

## If it exits non-zero

The state file violates the schema in CLAUDE.md (`Tier:` must be one of
trivial / quick / standard / full-cycle; `Stage:` an integer or `COMPLETE`). The
error names the offending field. Fix the header fields — put prose in `Notes:`,
which is unvalidated and free-form — then re-run. A malformed state file
silently breaks the session-start "resume from saved stage" rule, so repair it
rather than working around it.

`python scripts/pipeline_status.py --check` validates without printing, for use
in a hook or CI step.

This command never runs agents and never changes code.
