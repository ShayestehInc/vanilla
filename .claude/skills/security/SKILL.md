---
name: security
description: "Run only the security audit stage (Stage 9). Launches the ultrasecurity agent to scan for OWASP Top 10 vulnerabilities, secrets, auth bypass, and data exposure. Fixes critical/high issues."
---

# Security Stage (Stage 9)

Run the ultrasecurity agent for comprehensive security audit.

## Steps

1. **Read inputs**:
   - Read `tasks/dev-done.md` for list of changed files
   - Read `tasks/pipeline-state.md` for context

2. **Launch the ultrasecurity agent** via the Task tool:
   ```
   Task(
     subagent_type="ultrasecurity",
     prompt="You are running Stage 9 (Security) of the pipeline.

   Read tasks/dev-done.md for what was implemented and which files changed.
   Audit ALL changed files for security vulnerabilities.
   Also scan the ENTIRE codebase for secrets (API keys, tokens, passwords).
   Check: injection, auth/authz, IDOR, data exposure, CORS/CSRF, dependencies, third-party webhook signature validation.
   FIX all critical and high issues — don't just report.
   Run tests after fixes.
   Write your audit to tasks/security-audit.md.

   Follow all instructions in your agent prompt."
   )
   ```

3. **After the agent completes**:
   - Verify `tasks/security-audit.md` was written
   - Update `tasks/pipeline-state.md`
   - Git commit: `git add -A && git commit -m "stage 9 (ultrasecurity): security audit for [task name]"`

4. **Report** the security verdict and vulnerability counts to the user.
