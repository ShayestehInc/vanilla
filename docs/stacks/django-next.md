# Stack profile: Django + Next.js (default web)

The profile this boilerplate's gates were originally written against. Fully
worked, so use it as the reference when writing a new one.

## Layout

| Thing             | Path                                   |
| ----------------- | -------------------------------------- |
| Server code       | `backend/` (app-per-domain in `backend/apps/`) |
| Shared server lib | `backend/common/`                      |
| Client code       | `frontend/src/`                        |
| Server tests      | `backend/apps/<app>/tests/test_*.py`   |
| Client unit tests | `frontend/src/**/*.test.tsx` (jest)    |
| E2E tests         | `frontend/e2e/*.spec.ts` (Playwright)  |
| Scope helpers     | `backend/apps/users/scoping.py`        |

## Test commands

```bash
cd backend && python -m pytest --tb=short -q
cd frontend && npx tsc --noEmit
cd frontend && npx jest --ci
cd frontend && npx playwright test
cd backend && python -m mypy apps common config
cd backend && lint-imports --config .importlinter
```

## Local certification block

```bash
if grep -q '^backend/' <<<"$changed"; then
  run python3 scripts/check_isolation.py --base "$merge_base"
  run "$PY" backend/manage.py makemigrations --check --dry-run
  run "$PY" -m mypy apps common config
  run "$PY" -m pytest <changed apps' tests> -q
fi
if grep -q '^frontend/' <<<"$changed"; then
  run npx tsc --noEmit
  run npx jest --findRelatedTests $(grep '^frontend/' <<<"$changed")
  run npm run build
fi
```

`makemigrations --check` connects to a database. Against a dev DB it can fail
with `InconsistentMigrationHistory` — a property of that database, not of your
branch. Point it at a scratch name; Django then warns, skips the applied-history
check, and still performs the model-vs-migration drift check the gate is for.

## Platform

- Platform: web
- Breakpoints: 375 / 768 / 1024 px
- Keyboard navigation and visible focus rings are in scope for every UX pass.

## UI

- Component library: shadcn/ui — check for an existing component before building
  custom; never replace one, enhance with className overrides.
- Styling: Tailwind only, no CSS modules. `cn()` for conditional classes.
- Icons: lucide-react, never mixed with another set.
- Charts: recharts.
- Server components by default; `"use client"` only when needed.

## Stack rules the agents enforce

- API responses use `rest_framework_dataclasses`, not plain serializers.
- Services and utils return dataclasses or pydantic models, never `dict`.
- ORM only — no raw SQL.
- Background work goes to Celery; never block a request on third-party I/O.
- Strict typing: mypy on the server, no `any` or `!` on the client.

## Isolation gate configuration

```bash
ISOLATION_ROOT=backend/ \
ISOLATION_MIXIN=TenantIsolationMixin \
ISOLATION_ACTOR_MIXIN=ActorScopeMixin \
ISOLATION_TENANT_FK=tenant \
ISOLATION_SCOPED_BASES=TenantScopedModel,WorkspaceScopedModel \
  python3 scripts/check_isolation.py
```

Those are the gate's defaults, so the block is only needed if your project names
the mixin or FK differently. Whatever you choose, the names here, in
`CLAUDE.md`'s ISOLATION AXES, and in the code must be the same three names.

## Third-party providers

{{List each provider and whether it has inbound webhooks. Every inbound webhook
needs signature validation — the security agent reads this list.}}
