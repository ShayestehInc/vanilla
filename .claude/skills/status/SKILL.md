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

Reading two files and counting checkboxes is deterministic work, so a script does
it — exactly and for free — instead of a model narrating it.

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
