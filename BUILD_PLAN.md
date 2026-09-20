# Build Plan — {{PROJECT_NAME}}

The task list the orchestrator works through. One line per task. `[x]` when it
has shipped, not when it has been coded.

When every task is `[x]`, the orchestrator enters **Continuous Improvement
Mode**: it reads `PRODUCT_SPEC.md` for unbuilt features, looks for gaps, tech
debt, missing tests and UX regressions, appends the highest-impact one here as a
new `[ ]`, and runs the pipeline for it.

## Conventions

- `blocked by: #N` on a task defers it until N is `[x]`.
- Keep the number stable once assigned; artifacts and commits reference it.
- A task too big to describe in one line is an epic — write a brief in
  `docs/briefs/` and link it.

## Phase 1 — {{foundation}}

- [ ] 1. {{Task}} — {{one-line outcome}}
- [ ] 2. {{Task}} — blocked by: #1

## Phase 2 — {{…}}
