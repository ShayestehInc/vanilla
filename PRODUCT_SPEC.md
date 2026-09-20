# Product Spec — {{PROJECT_NAME}}

The complete statement of what is being built. `BUILD_PLAN.md` is the *order*;
this is the *what and why*. The planner agent reads this when deciding what to
build next, so vagueness here becomes vagueness in the tickets.

## 1. Problem & users

- Who has the problem, and what do they do today instead?
- What outcome makes this a success? Name a measurable one.

## 2. Personas & permissions

| Persona | What they can see | What they can do | Lands on |
| ------- | ----------------- | ---------------- | -------- |
| {{}}    |                   |                  |          |

If any persona sees a subset of a tenant's data, that is an isolation axis —
define it in `CLAUDE.md` under ISOLATION AXES before any code is written.

## 3. Domain model

The nouns, their relationships, and which of them are tenant-scoped.

## 4. Surfaces

Per screen/endpoint: purpose, the data it shows, the actions it offers, and the
empty / loading / error states. A surface with no specified empty state will get
a bad one.

## 5. Non-functional requirements

- Scale: {{records, concurrent users, request rate}}
- Latency budget: {{}}
- Availability & what "down" costs
- Data retention and deletion
- Compliance: {{}}

## 6. Out of scope (for now)

Being explicit here is what stops the pipeline from gold-plating.
