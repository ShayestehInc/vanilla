---
name: ux
description: "Run only the UX audit stage (Stage 8). Launches the ultraux agent for comprehensive UX evaluation — states, copy, accessibility, consistency, responsiveness. Fixes issues directly."
---

# UX Stage (Stage 8)

Run the ultraux agent for UX audit and polish.

## Steps

1. **Read `tasks/pipeline-state.md`** for the task name — the agent reads the
   stage artifacts itself, so don't pre-read them here.

2. **Launch the ultraux agent** via the Agent tool:
   ```
   Agent(
     subagent_type="ultraux",
     prompt="You are running Stage 8 (UX) of the pipeline.

   Read tasks/next-ticket.md for UX requirements.
   Read tasks/ui-design.md for design specifications.
   Audit all UI code for this feature: states, copy, accessibility, consistency, responsiveness.
   Implement fixes — don't just report.
   Run tests after changes.
   Write your audit to tasks/ux-audit.md.

   Follow all instructions in your agent prompt."
   )
   ```

3. **After the agent completes**:
   - Verify `tasks/ux-audit.md` was written and fixes were applied
   - Update `tasks/pipeline-state.md`
   - Git commit: `git add -A && git commit -m "stage 8 (ultraux): UX audit for [task name]"`

4. **Report** the UX score and key findings to the user.
