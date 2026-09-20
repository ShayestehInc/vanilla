---
description: Record a video proving the work you just finished actually works
---

Produce a proof video of the change you just made.

1. Read `demos/current.spec.ts` for the shape, then **overwrite it** with a
   walkthrough of what you just built. Keep it under ~8 steps and under 60
   seconds of runtime.

2. Rules for the spec — these are not negotiable:
   - Every claim the video makes must have a matching `expect()`. The video is
     the artifact; the assertions are the proof.
   - Assert on user-visible state (text, roles, URLs), never on internals.
   - No `try`/`catch` around assertions, no `test.skip`, no conditionals that
     let a broken flow pass.
   - Where it's cheap, prove persistence: reload and re-assert.
   - If the change fixed a bug, demonstrate the previously-broken path.

3. Run it:
   ```
   bash scripts/record-demo.sh <short-slug>
   ```

4. If the run fails, that is a real finding. Do not weaken the assertions to
   make it pass. Fix the app, or tell me the flow doesn't work yet.

5. Report back with: the video path (and link, if upload is configured), a
   one-line summary of what the video shows, and anything you were **not** able
   to demonstrate.
