# ADR-0007: Send mode fails closed

Status: Accepted (design PR #1 merged 2026-10-22). Date: 2026-10-22. Deviates from brief §1.3.

## Context

In calling-agent-2, test mode is "`ONLY_TO` is set"; going live means deleting it. That fails
open: a new environment (a new GitHub repo secret set, a fork, a local `.env`) that simply never set
`ONLY_TO` sends to real prospects.

## Decision

- `SEND_MODE` = `test` (default when unset or anything other than `live`) or `live`.
- In `test`, the allow-list is `ONLY_TO` (env) ∪ `constraints.test_mode_only_to` (offer.yaml).
  Every approved message to anyone else becomes `held`. Internal addresses skip send windows.
- Going live = setting `SEND_MODE=live` for that environment: still one variable, done through
  `/go-live`, which first runs `si check` and the end-to-end test-mode checklist and records who
  switched it and when.
- Held messages are not released automatically when going live; the operator re-approves or
  bulk-releases them, because they may be stale.
- The dashboard shows a large "TEST MODE" banner while in test mode.

## Consequences

- An unconfigured environment can never send live.
- Slightly different from the brief's wording; the intent (one variable, test mode first-class) holds.
