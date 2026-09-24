---
name: research
description: "Run only the research stage (Stage 2). Launches the ultraplanner agent (SCOPE: research-only) to deep-dive into the codebase, discover patterns, analyze dependencies, and produce a research report."
---

# Research Stage (Stage 2)

Run the ultraplanner agent in research-only scope for comprehensive codebase and dependency analysis.

## Steps

1. **Read `tasks/pipeline-state.md`** for the task name — the agent reads the
   stage artifacts itself, so don't pre-read them here.

2. **Launch the ultraplanner agent** via the Task tool:
   ```
   Task(
     subagent_type="ultraplanner",
     prompt="You are running Stage 2 (Research) of the pipeline.
   SCOPE: research-only

   Read tasks/next-ticket.md for the implementation ticket.
   Deep-dive into the codebase to find all relevant files, patterns, and dependencies.
   Write your research report to tasks/research-report.md.

   Follow all instructions in your agent prompt."
   )
   ```

3. **After the agent completes**:
   - Verify `tasks/research-report.md` was written
   - Update `tasks/pipeline-state.md`
   - Git commit: `git add -A && git commit -m "stage 2 (ultraplanner/research): research report for [task name]"`

4. **Report** key findings to the user.
