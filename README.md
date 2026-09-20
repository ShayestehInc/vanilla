# vanilla — an agentic build pipeline boilerplate

A drop-in `.claude/` + gates + docs skeleton that turns Claude Code into a
multi-stage build pipeline: plan → research → design → dev → review → fix → QA →
UX → security → arch → chaos → verify, with the depth chosen by the task's risk.

It is stack-agnostic. Web, mobile, or both — you pick a **stack profile** and the
agents read it.

## What's in here

```
CLAUDE.md                  the orchestrator contract — read this first
.claude/agents/            16 specialised agents (one per stage, + polish + ticketsmith)
.claude/skills/            22 slash commands that drive them
.claude/rules/             always-on coding rules
.claude/hooks/             file-size guardrail wired into Write/Edit
.claude/settings.json      hook wiring + lint-on-save
scripts/check_code_size.py         400-line file / 50-line function gate
scripts/check_known_failures.py    every failing test needs an owner and an expiry
scripts/check_isolation.py         AST gate: no unscoped multi-tenant endpoint
scripts/pipeline_status.py         /status, with --check validation of the state file
scripts/archive_artifacts.py       archive one run's artifacts
scripts/local-ci-certify.sh        run CI locally, publish a commit status
scripts/local-ci-change-policy.sh  fail-closed eligibility for that cheap lane
.githooks/pre-push                 refuses an eligible-but-uncertified push
docs/stacks/                       stack profiles; ACTIVE.md is the one in force
tasks/                             pipeline artifacts + tickets live here
```

## The idea worth keeping

Three ideas, actually, and they are why this is more than a prompt collection:

1. **Route by risk, not by size.** A three-line change to tenant-isolation code
   gets the full Dev → Review → Fix loop; a 200-line copy change does not. The
   Trivial/Quick split in `CLAUDE.md` is the cheapest quality lever here.
2. **An agent can narrate compliance with a rule it isn't measured against.**
   Every rule in `CLAUDE.md` that matters has a script in `scripts/` that fails
   the build. The prose exists to explain the script, not to replace it.
3. **CI red must mean something.** A failing test needs an owner and an expiry
   or it is a bug, not a known issue. A gate everyone ignores costs the same as
   a real one and certifies nothing.

## Instantiating it

```bash
cp -r vanilla/ my-project/ && cd my-project && git init
scripts/install-git-hooks.sh
cp docs/stacks/django-next.md docs/stacks/ACTIVE.md   # or flutter.md, or write one
```

Then, in order:

- [ ] Fill every `{{placeholder}}` in `CLAUDE.md` — especially the **Project**,
      **Tech Stack** and **ISOLATION AXES** sections.
- [ ] Fill in `docs/stacks/ACTIVE.md`. Agents run the commands it lists, so a
      stale one is worse than a missing one.
- [ ] Paste the stack-specific block into `scripts/local-ci-certify.sh` (marked
      `{{CUSTOMIZE}}`) and tune the risk pattern in
      `scripts/local-ci-change-policy.sh`.
- [ ] Configure `scripts/check_isolation.py` for your mixin/FK names, or delete
      it if the product is single-tenant.
- [ ] Wire `check_code_size.py` and `check_known_failures.py` into your CI lint
      job, and add the `local/fast-ci` short-circuit to the gate job.
- [ ] Write `PRODUCT_SPEC.md`, then seed `BUILD_PLAN.md` with the first tasks.
- [ ] Delete what you don't use. An unused agent is context you pay for.

Verify the skeleton still validates:

```bash
python3 scripts/pipeline_status.py --check
```

## Daily use

```
/ticket "reps can see other reps' calls on the dashboard"   # spec it
/quick        # bug fix or low-risk change with a ticket
/standard     # a medium feature
/full-cycle   # a new system, or anything high-risk
/status       # where is the run?  (no model call)
/commit       # grouped commits
```

The orchestrator resumes from `tasks/pipeline-state.md`, so a context reset
mid-run is recoverable: type `continue`.

## Provenance

Distilled from a production Django + Next.js operations platform. The sharp
edges are deliberate: most of the numbered rules exist because something shipped
broken without them, and the commentary in the gate scripts explains which.
