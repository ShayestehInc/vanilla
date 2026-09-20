# Stack profile: {{NAME}}

## Layout

| Thing            | Path            |
| ---------------- | --------------- |
| Server code      | {{backend/}}    |
| Client code      | {{frontend/}}   |
| Server tests     | {{}}            |
| Client unit tests| {{}}            |
| E2E tests        | {{}}            |
| Scope helpers    | {{module that owns tenant/actor scope queries}} |

## Test commands

```bash
# server unit + integration
{{}}
# client unit
{{}}
# e2e
{{}}
# type check / lint
{{}}
```

## Local certification block

The stack-specific half of `scripts/local-ci-certify.sh`:

```bash
{{paste the exact scoped commands here}}
```

## Platform

- Platform(s): {{web | mobile | both}}
- Web breakpoints: {{375 / 768 / 1024}}
- Mobile device matrix: {{small phone, large phone, tablet; min OS versions}}

## UI

- Component library: {{}}
- Styling: {{}}
- Icon set (never mix sets): {{}}
- Design tokens live in: {{}}

## Third-party providers

{{list each provider and whether it has inbound webhooks that need signature
validation — the security agent reads this}}

## Known-flaky policy

{{Which suites are re-run-first, and the evidence. Empty is the correct
starting value; do not pre-populate it with guesses.}}
