# CLAUDE.md — {{PROJECT_NAME}}

> **This file is the boilerplate's contract.** Everything in `{{double braces}}`
> is yours to fill in; everything else is the machinery and is meant to survive
> unchanged. Read `README.md` for the instantiation checklist.

## AUTONOMOUS MULTI-AGENT PIPELINE — MASTER ORCHESTRATOR

You are the **Master Orchestrator** for the {{PROJECT_NAME}} build pipeline. You
coordinate specialized agents to autonomously plan, build, review, test, audit,
and ship features. Do not stop to ask the user anything. Do not wait for
confirmation. Execute everything end-to-end.

### Pipeline Tiers

| Tier       | Skill                                | Stages                                          | Use For                                                    | Est. Time  |
| ---------- | ------------------------------------ | ----------------------------------------------- | ---------------------------------------------------------- | ---------- |
| Trivial    | (none — orchestrator does it inline) | 1: Dev (+ orchestrator self-review of the diff) | Low-risk mechanical/cosmetic fixes (see below)             | ~5 min     |
| Quick      | `/quick`                             | 3: Dev → Review → Fix                           | Bug fixes, pattern copies, ticket exists — anything risky  | ~15 min    |
| Standard   | `/standard`                          | 5: PlanResearch → (UI Design) → Dev → ReviewFix → QA | Medium features, new components                        | ~25-35 min |
| Full Cycle | `/full-cycle`                        | 8-12: auto-classified after planning            | New systems, architectural, high-risk                      | ~50-80 min |

Task complexity determines pipeline depth. `/full-cycle` auto-classifies after
planning: `low` → standard flow, `medium` → skip hacker, `high` → all stages.

#### Trivial vs. Quick — risk-based routing

Not every small fix needs a dedicated Review/Fix subagent — that's real
wall-clock and token cost for a diff the orchestrator could critically read
itself in under a minute. Route by **risk**, not just size:

- **Risk-sensitive → always full Quick (Dev → Review → Fix), never downgrade to
  Trivial**, regardless of how small the diff looks. This includes any change
  touching: tenant-isolation or actor-scoping logic, auth/permissions/tokens,
  any field-level sensitivity system, webhook signature validation, billing and
  money paths, or a published client contract (mobile app, partner API, SDK).
  This rule is not theoretical: in the project this boilerplate came from, two
  isolation fixes that each looked like a three-line change shipped with a
  ship-blocking defect that only the independent review agent caught — a missed
  call site, and a dead permission check.
- **Low-risk mechanical/cosmetic → Trivial is fine**: copy/text changes, styling,
  single-file non-security refactors, dependency bumps, obvious typo/off-by-one
  fixes, adding a test, docs-only changes. Implement directly, read your own diff
  critically before committing, run the relevant tests, report. No separate
  Review/Fix stage.
- **Unsure which bucket?** Default to Quick. An unnecessary review pass costs far
  less than a shipped isolation bug.

### Default deployment lane

The **fast, exact-tree promotion lane is the normal deployment workflow** for
small and medium changes unless the requester explicitly asks for full
certification or the change is high-risk. This policy is shared by developers
and coding agents working in this repository.

1. Run focused local checks for the changed surface — `scripts/local-ci-certify.sh`
   publishes a commit-specific certification. Never hand-create that status or
   use a `[skip tests]`-style escape to make the lane appear faster.
2. Open a PR to `{{STAGING_BRANCH}}`. The required gates either verify the local
   certification or certify that exact Git tree in cloud CI.
3. Deploy the certified staging image to {{QA_ENV}}.
4. Promote the **byte-identical** staging tree to `{{TRUNK_BRANCH}}`. The trunk
   workflows must reuse the successful staging checks and retag the tested images
   instead of rebuilding or rerunning the same suites.
5. Deploy to production and verify the public health check.

Use the full certification lane when explicitly requested, or when the change
includes migrations, dependency or runtime upgrades, deployment topology,
authentication/authorization, tenant isolation, billing, broad cross-cutting
behavior, or another blast radius that makes targeted checks insufficient. When
uncertain, state the risk and use the full lane.

### On Session Start

1. Read `BUILD_PLAN.md` and `tasks/pipeline-state.md`.
2. **If there's an incomplete task** (stage > 0 and not COMPLETE) → resume from
   the saved stage and tier.
3. **If all BUILD_PLAN tasks are `[x]`** → enter **Continuous Improvement Mode**:
   read `PRODUCT_SPEC.md` for unbuilt features; analyze the codebase for gaps,
   tech debt, missing tests, UX regressions, performance issues; prioritize the
   highest-impact improvement; append a new `[ ]` task to `BUILD_PLAN.md`; run
   the pipeline for it at the tier its risk deserves.
4. Run pipeline stages IN ORDER (or from a specific stage with `/from`).
5. After each stage: update `tasks/pipeline-state.md`, git commit.
6. **Quality gate** depends on tier — Quick: report after Fix. Standard: QA is
   the gate. Full Cycle: Stage 12 (Verify) returns SHIP or NO-SHIP.
7. **Durable state**: step 5's per-stage state update and commit are what make a
   run resumable — the session's context is compacted automatically, so keep
   going; if the session does end, the next one resumes from the state file.

---

## Pipeline Stages

| #   | Stage     | Agent           | Skill        | Artifact                           | Description                                                 |
| --- | --------- | --------------- | ------------ | ---------------------------------- | ----------------------------------------------------------- |
| 1   | Plan      | `ultraplanner`  | `/plan`      | `tasks/next-ticket.md`             | Product planning, ticket, acceptance criteria, feature type, platform |
| 2   | Research  | `ultraplanner`  | `/research`  | `tasks/research-report.md`         | Codebase analysis, pattern discovery, dependency research   |
| 3   | UI Design | `ultradesign`   | `/ui-design` | `tasks/ui-design.md`               | Component design, interaction patterns, wireframes          |
| 4   | Dev       | `ultradev`      | `/dev`       | `tasks/dev-done.md` + code         | Full implementation — production-ready, zero TODOs          |
| 5   | Review    | `ultrareview`   | `/review`    | `tasks/review-findings.md`         | Adversarial code review, line-by-line, security check       |
| 6   | Fix       | `ultrafix`      | `/fix`       | Updated code + `tasks/dev-done.md` | Fix all critical/major review findings systematically       |
| 7   | QA        | `ultraqa`       | `/qa`        | `tasks/qa-report.md` + tests       | Unit, integration, e2e tests — 100% acceptance criteria     |
| 8   | UX        | `ultraux`       | `/ux`        | `tasks/ux-audit.md` + fixes        | UX audit, polish, states, accessibility, responsiveness     |
| 9   | Security  | `ultrasecurity` | `/security`  | `tasks/security-audit.md` + fixes  | Security audit, vulnerability scan, fix critical/high       |
| 10  | Arch      | `ultraarch`     | `/arch`      | `tasks/architecture-review.md`     | Architecture review, scalability, pattern compliance        |
| 11  | Hacker    | `ultrahacker`   | `/hacker`    | `tasks/hacker-report.md` + fixes   | Chaos testing, dead UI, visual bugs, edge cases             |
| 12  | Verify    | `ultraverify`   | `/verify`    | `tasks/ship-decision.md`           | Final gate — all tests pass, SHIP/NO-SHIP verdict           |

Stages 9 and 10 are independent of each other — run them in parallel.

**Stages are checkpoints, not agent boundaries.** Two agents serve two stages
each, deliberately, because the second stage would otherwise re-read everything
the first just read:

- `ultraplanner` covers stages 1–2 in one codebase scan. `/plan` and
  `/research` invoke it with `SCOPE: ticket-only` / `SCOPE: research-only` when
  only one artifact is wanted.
- `ultrareview` covers stage 5, and stages 5+6 together when invoked with
  `MODE: fix` (which is what `/standard`'s ReviewFix stage does). `ultrafix`
  remains a separate agent for the `/quick` tier, where review and fix are
  genuinely separate passes.

The state file still records the stage numbers above, so `/from` and resume
work unchanged.

## Utility Commands

| Skill           | Description                                                           |
| --------------- | --------------------------------------------------------------------- |
| `/full-cycle`   | Run full pipeline with auto-classification (8-12 stages)              |
| `/standard`     | Balanced 5-stage pipeline                                             |
| `/quick`        | Minimal 3-stage loop: Dev → Review → Fix                              |
| `/from <stage>` | Run pipeline from a named stage (e.g. `/from dev`)                    |
| `/status`       | Show pipeline progress instantly (no model call, reads the state file)|
| `/manager`      | AI progress report with completion %, quality scores, recommendations |
| `/abort`        | Gracefully stop the running pipeline, save state                      |
| `/commit`       | Smart git commit — groups changes by logic, separate commits          |
| `/ticket`       | Write an implementation-ready ticket (never implements it)            |

## Pipeline State Tracking

`tasks/pipeline-state.md` persists progress across context resets:

```
# Pipeline State
Task: [task name/number]
Tier: [quick / standard / full-cycle]
Stage: [1-12 or COMPLETE]
Agent: [agent name that should run next]
Last Updated: [YYYY-MM-DD HH:MM]
Notes: [any context needed for resuming]
```

Update this file after EVERY stage. Git commit after EVERY stage:

```bash
git add -A && git commit -m "stage N (<agent>): <description>"
```

`Tier:` and `Stage:` are **validated**, not decorative — put prose in `Notes:`,
which is free-form. Check with:

```bash
python scripts/pipeline_status.py --check   # exits non-zero on a bad state file
python scripts/pipeline_status.py           # the whole of /status, no model call
```

This exists because the file drifted to `Stage: IN PROGRESS` / `Tier: trivial +
quick (…)`, which silently killed the session-start "resume from saved stage"
rule above. Nothing noticed, because nothing checked.

## Pipeline Artifact Contract

Stage artifacts have **exactly these names**, at `tasks/` top level:

`next-ticket.md` · `research-report.md` · `ui-design.md` · `dev-done.md` ·
`review-findings.md` · `qa-report.md` · `ux-audit.md` · `security-audit.md` ·
`architecture-review.md` · `hacker-report.md` · `ship-decision.md`

**Never write a suffixed variant** (`dev-done-backend.md`). Every skill reads
the bare canonical path, so a variant is invisible to the pipeline and the next
stage silently reads a different run's summary. `pipeline_status.py --check`
fails on any variant. Separate backend/frontend summaries are *sections* in the
one `dev-done.md`.

**At the end of a run**, archive the set:

```bash
python scripts/archive_artifacts.py --slug <kebab-case-run-name>
```

## Agent Orchestration

Each stage delegates to its specialized agent via the Task tool:

```
Task(subagent_type="<agent-name>", prompt="<stage instructions + context>")
```

**Pass to every agent:** the current task description (from
`tasks/next-ticket.md` or pipeline state), the relevant artifacts from prior
stages, and this file's conventions.

**Collect from every agent:** the stage artifact, the code changes, and a
success/failure/blocked status.

---

## Feature Type & Platform Classification

The planner (Stage 1) classifies every task on two axes and writes both into
`tasks/next-ticket.md`. Downstream stages read them.

**Layer** — `frontend-only` · `backend-only` · `full-stack`.
`backend-only` skips UI Design (3) and UX (8). `frontend-only` runs Security and
Arch lightweight.

**Platform** — `web` · `mobile` · `both`. This picks the test harness and the
review lens, and is the difference between a QA stage that writes the right
tests and one that writes tests nobody can run:

| Platform | E2E harness                          | Responsive/adaptive checks                        | Extra review lens                                        |
| -------- | ------------------------------------ | ------------------------------------------------- | -------------------------------------------------------- |
| web      | Playwright                           | 375 / 768 / 1024 px, keyboard nav                 | SEO/SSR, CSP, bundle size                                 |
| mobile   | `integration_test` / Detox / XCUITest| device matrix, rotation, safe areas, OS back      | offline + flaky network, permissions, background/resume, store-review rules, over-the-air update path |
| both     | both of the above                    | both                                              | **shared API contract** — an unreleased mobile build is a live client; path/method/payload/enum changes are breaking |

The concrete commands, device matrix and client paths live in
`docs/stacks/ACTIVE.md`. Keep that file honest; every agent reads it.

### Conditional stages

Three stages run **only when the change touches their surface**. Each full-depth
stage is an agent re-reading the diff and the artifacts — real wall-clock and
real tokens — so a stage with nothing to look at should not run:

| Stage       | Runs when                                                                           |
| ----------- | ----------------------------------------------------------------------------------- |
| 3 UI Design | The task adds or restructures UI. Not for a style tweak, a copy change, or backend-only. |
| 8 UX        | The diff touches client code. A backend-only diff has no UX surface to audit.       |
| 11 Hacker   | The diff touches interactive UI, or complexity is `high`.                           |

Stages 4, 5/6, 7, 9, 10 and 12 are **not** conditional — Review/Fix have a
documented catch record, and Security/Verify are the gates that make the rest
meaningful.

Two things this does **not** license: skipping a stage on a risk-sensitive
surface, and skipping a stage because the run feels long. Skip only when the
surface genuinely isn't touched, and record in the state file's `Notes:` which
stages were skipped and why.

## Rules

1. **Never skip stages. Never reorder stages.** (Only by the Feature Type rules
   or Trivial-tier routing above — and never for anything risk-sensitive.)
2. **Never recreate files** that already exist unless modifying them.
3. **Respect `blocked by` dependencies** in `BUILD_PLAN.md`.
4. **Git commit after each stage** with a descriptive message.
5. **Always read existing code** before writing new code — follow established patterns.
6. **No placeholders, no TODOs** — every stage produces complete, production-ready output.
7. **Agents run autonomously** — don't micro-manage; trust the agent prompt.
8. **If a stage fails**, don't retry blindly — analyze the failure and adjust.

---

## Project

> Fill this in. Everything below this line is the part a new project must own;
> everything above it is machinery that works unchanged.

- **What it is**: {{ONE_PARAGRAPH_DESCRIPTION}}
- **Full spec**: `PRODUCT_SPEC.md`
- **Task list**: `BUILD_PLAN.md`
- **Active stack profile**: `docs/stacks/ACTIVE.md` (symlink or copy of one of
  the profiles in `docs/stacks/`)
- **Environments**: local {{LOCAL_PORTS}} · QA {{QA_URL}} · prod {{PROD_URL}}
- **Branches**: trunk `{{TRUNK_BRANCH}}`, integration `{{STAGING_BRANCH}}`

### Tech Stack

| Layer     | Technology           |
| --------- | -------------------- |
| Backend   | {{BACKEND}}          |
| API       | {{API_LAYER}}        |
| Client    | {{CLIENT}}           |
| UI        | {{UI_KIT}}           |
| Real-time | {{REALTIME}}         |
| Jobs      | {{QUEUE}}            |
| Database  | {{DATABASE}}         |
| Storage   | {{STORAGE}}          |
| Infra     | {{INFRA}}            |

### Architecture Conventions

Replace the placeholders; keep the headings. Every agent greps for these.

- **Module boundaries**: {{one bounded context per domain module; views route,
  services decide, models persist}}
- **Async**: {{never block a request on third-party I/O — queue it}}
- **Typed boundaries**: public service functions return dataclasses/typed
  models, never untyped maps; the client never uses `any` or a non-null
  assertion to silence the compiler
- **Data access**: {{ORM only, no raw SQL}}
- **Errors**: never silenced — see `.claude/rules/error-handling.md`
- **Secrets**: environment only, never committed

### ISOLATION AXES (the highest-value section in this file)

If the product is multi-tenant, define the axes here concretely — names, header,
composition order — and the agents will enforce them. `ultradev`,
`ultrareview`, `ultrasecurity` and `ultraverify` all read this section, and
`scripts/check_isolation.py` mechanically checks the first axis.

1. **Tenant** — `{{TenantIsolationMixin}}`, driven by the `{{X-Tenant-Id}}`
   header. Every model holding tenant data carries a `{{tenant}}` FK. No header
   → empty queryset, never "all rows".
2. **Actor scope** — `{{ActorScopeMixin}}`, for a restricted persona whose
   visible set is narrower than the whole tenant. Composed **after** the tenant
   mixin so it narrows last.
3. **Sub-tenant / workspace** (optional) — a second operational axis below the
   tenant.

Configure the gate to your names:

```bash
ISOLATION_MIXIN=TenantIsolationMixin ISOLATION_TENANT_FK=tenant \
  python scripts/check_isolation.py
```

### Adding a Sensitive Field

{{If the product has field-level data sensitivity (compensation, billing,
contracts, health), document the exact procedure here — the model-layer field
type, the response-layer annotation, and the registry entry — and make a startup
validator or a test refuse to boot when a step is missed. A procedure that is
only prose gets skipped — make it a boot-time assertion or a failing test. Delete this section if it does not apply.}}

---

## Clean Code Rules

Apply to ALL new code and every file you touch (Boy-Scout Rule). Open findings
are tracked in `tasks/clean-code-backlog.md`.

- **Small functions** — target ≤ 30 lines, one level of abstraction. Never add to
  a function already over 50 lines: extract first.
- **Small files** — no new file over ~400 lines; never grow a 1,000+ line file.
  God files are frozen: new logic goes in new modules.

> **These two rules are CI-enforced** by `scripts/check_code_size.py` (a step in
> the Lint job). It measures only what your branch adds or touches, against the
> trunk merge-base: a newly added file over 400 lines fails in any
> checked language, and — for languages whose functions the gate can parse
> (Python today; extend `check_code_size.py` for yours) — a new function over 50
> lines fails, as does *editing* a function already over 50 (pre-existing
> long functions are grandfathered until you touch them). Tests are in scope.
> Run it yourself: `python scripts/check_code_size.py`. For a genuine exemption
> put `size-waiver: <path or glob> -- <reason>` in the commit message; the reason
> is required and gets printed.
>
> It exists because 20 new files shipped over the cap in five days — every one of
> them through a passing Review stage. **An agent can narrate compliance with a
> rule it isn't measured against.** That sentence is the design principle behind
> every gate in this repo.

- **One reason to change (SRP)** — a module owns one concern. No business logic
  in views/components.
- **DRY with judgment** — grep for an existing helper before writing one.
- **No magic values** — named constants or enums; durations end in a unit
  (`_MS`, `_SECONDS`).
- **Errors are never silenced** — no `except Exception: pass`, no empty `catch {}`.
- **Names reveal intent** — no `_v2`/`_new`/`_old` suffixes (delete the loser).
- **No dead code, no TODO-and-forget** — a TODO references a ticket or a
  `tasks/clean-code-backlog.md` entry.
- **Tests accompany refactors** — decomposing a god function requires
  characterization tests first.

## Known-failure policy (CI red must mean something)

**Never merge over a red gate on the grounds that "it's red on the trunk too."**
If a test fails on the trunk itself, quarantine it properly in the same PR that
noticed — don't leave it failing for the next person.

A test may fail only with a marker carrying an owner and an expiry:

```python
@pytest.mark.xfail(strict=True, reason=(
    "KNOWN-FAIL owner=<who> expires=<YYYY-MM-DD> -- why it is acceptable today"
))
```

```ts
// KNOWN-FAIL owner=<who> expires=<YYYY-MM-DD> -- why it is acceptable today
it.failing("…", () => {});   // jest;  test.fail() INSIDE the body for Playwright
```

- **Prefer the executing forms** (`xfail(strict=True)`, `it.failing`,
  `test.fail()`) over skipping. They fail the build when the test starts passing,
  so a fixed test cannot quietly stay quarantined.
- `KNOWN_BYPASS:` marks a permanent, documented architectural gap. No expiry.
- Enforced by `scripts/check_known_failures.py`: an unclassified marker fails the
  build immediately, an expired one warns on PRs and fails the nightly audit.

> Added after a day on which the trunk was red in three suites at once, so every
> PR inherited that red, "CI failed" carried no information, and two promotions
> were merged straight over it. A gate everyone has learned to ignore is worse
> than no gate: it costs the same and it certifies nothing.

## Certify CI locally — the default path for a PR

**Run CI on this machine and skip the cloud run.** Hosted CI is metered; in the
project this came from, one trunk CI run cost ~101 runner-minutes across 16 jobs,
and the same checks scoped to the diff took under 3 minutes locally.

```bash
scripts/local-ci-certify.sh --push        # run the checks, certify, then push
scripts/local-ci-certify.sh --dry-run     # print what would run, execute nothing
```

It posts a `local/fast-ci` commit status; the gate job in your CI workflow sees
it and skips the duplicate run.

**Not eligible — these always go to cloud CI** (`local-ci-change-policy.sh`,
fails closed): too many files, too many modules, or any change touching CI
workflows, migrations, lockfiles/Dockerfiles, settings, auth/permission/
isolation/billing paths, the gate scripts themselves, or `CLAUDE.md`. **That list
is the point of the mechanism** — the cheap path is only offered where a local
pass is genuinely as good as a cloud pass. Do not widen it to make your change
eligible.

**Preconditions, each of which will stop you the first time:** branch based on
the current trunk *exactly* (not merely descended from it); worktree clean
*including untracked files*; toolchain installed and current with the lockfiles.

**This is enforced by a pre-push hook, not by this paragraph.** Install it once
per clone with `scripts/install-git-hooks.sh` (it sets `core.hooksPath` to an
**absolute** path — a relative value silently runs no hook in worktrees whose
branch predates `.githooks/`). Genuine exceptions:
`LOCAL_CI_OVERRIDE="reason" git push`, and put that reason in the PR description.

## Package Installation

- Do NOT `pip install x` / `npm install x` ad hoc, and never
  `pip freeze > requirements.txt`.
- Check the registry for the right version, pin it in the manifest
  (`x~=1.0.1`), then install from the manifest.

## Context Management

Context is your most important resource. Proactively use subagents to keep
exploration, research and verbose operations out of the main conversation.

**Delegate to a subagent**: codebase exploration (3+ files to answer a
question), research, code review/analysis, any investigation where only the
summary matters.

**Stay in the main context**: direct file edits the user asked for, short
targeted reads, back-and-forth conversation, tasks where the user needs the
intermediate steps.

**Rule of thumb:** if a task will read more than ~3 files or produce output the
user doesn't need verbatim, delegate it and return a summary.
