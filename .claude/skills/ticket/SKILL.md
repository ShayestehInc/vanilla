---
name: ticket
description: "Write an implementation-ready ticket (no implementation). Turns an idea, transcript, bug report, or feature request into tasks/tickets/NNN-slug.md via the ticketsmith agent. Use when the user wants something specced, not built."
---

# /ticket

Draft a ticket. **Never implement it.**

1. If the user gave no subject, ask what the ticket should cover — one question, then proceed.
2. Delegate to the `ticketsmith` agent via the Agent tool, passing:
   - the raw request verbatim (plus any transcript/file the user pointed at)
   - any constraints the user stated (deadline, client, who will build it)
3. Relay back: ticket path, title, priority/complexity/suggested tier, risk surfaces touched,
   and any Open Questions the agent could not resolve.

Multiple distinct asks in one message → one ticket each, agents launched in parallel.

Do not run `/quick`, `/standard`, `/full-cycle`, or edit app code from this skill.
