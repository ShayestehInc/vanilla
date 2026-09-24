---
name: quick
description: "Run the minimal 3-stage pipeline loop: Dev → Review → Fix. Use when the ticket already exists and you want a fast build-review-fix cycle without full audits."
---

# Quick Pipeline (Dev → Review → Fix)

Run a minimal 3-stage loop for fast iteration.

## When to Use

- The planning ticket (`tasks/next-ticket.md`) already exists
- You want fast implementation without full QA/UX/security audits
- Iterating on existing code that doesn't need architectural review

## Steps

1. **Verify prerequisites**:
   - `tasks/next-ticket.md` must exist — if not, run `/plan` first
   - Read `tasks/pipeline-state.md` for context, then initialize it:
     ```
     # Pipeline State
     Task: [task name]
     Tier: quick
     Stage: 1
     Agent: ultradev
     Last Updated: [now]
     Notes: Starting quick pipeline
     ```
     The quick tier numbers its own stages 1–3 (Dev, Review, Fix) — the numbers
     `scripts/pipeline_status.py` validates and `/from` maps.

2. **Run Stage 1 (Dev)**: Launch the ultradev agent
   ```
   Agent(
     subagent_type="ultradev",
     prompt="Quick pipeline — Stage 1 (Dev).
   Read tasks/next-ticket.md. Implement the feature completely.
   Write summary to tasks/dev-done.md."
   )
   ```
   - Advance `Stage:`/`Agent:` in `tasks/pipeline-state.md`, then git commit

3. **Run Stage 2 (Review)**: Launch the ultrareview agent
   ```
   Agent(
     subagent_type="ultrareview",
     prompt="Quick pipeline — Stage 2 (Review).
   Read tasks/next-ticket.md and tasks/dev-done.md.
   Review all changed files. Write findings to tasks/review-findings.md."
   )
   ```
   - Advance `Stage:`/`Agent:` in `tasks/pipeline-state.md`, then git commit

4. **Run Stage 3 (Fix)**: Launch the ultrafix agent
   ```
   Agent(
     subagent_type="ultrafix",
     prompt="Quick pipeline — Stage 3 (Fix).
   Read tasks/review-findings.md. Fix all critical and major issues.
   Run tests. Update tasks/dev-done.md."
   )
   ```
   - Set `Stage: COMPLETE` in `tasks/pipeline-state.md`, then git commit

5. **Report** summary: what was built, review score, fixes applied, test results.

## Closing the run (required)

When the final stage of this pipeline passes, archive the artifact set so the
next run starts from an unambiguous `tasks/`:

```bash
python scripts/archive_artifacts.py --slug <kebab-case-run-name>
python scripts/pipeline_status.py --check   # must exit 0 before you report done
```

Never write a suffixed artifact variant (`dev-done-backend.md`) — see
"Pipeline Artifact Contract" in CLAUDE.md. The check fails on them.
