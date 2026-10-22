# Architecture decision records

One file per decision. Status is `Proposed` until the operator approves the design, then
`Accepted`. A later ADR can supersede an earlier one; we never rewrite an accepted ADR's decision.

| # | Decision | Status |
|---|---|---|
| [0001](0001-licence.md) | MIT licence; AGPL tools only as separate services | Accepted |
| [0002](0002-database.md) | New Supabase project, plain-SQL migrations that also run on plain Postgres | Accepted |
| [0003](0003-scheduler.md) | GitHub Actions cron with windowed send runs | Accepted |
| [0004](0004-dashboard-and-public-endpoints.md) | Next.js web app for dashboard + always-on public endpoints | Accepted |
| [0005](0005-llm-access.md) | Anthropic API via the SDK behind one `generate_json`, with a cost meter | Accepted |
| [0006](0006-logic-less-templates.md) | Logic-less Mustache templates shared by engine and dashboard | Accepted |
| [0007](0007-send-mode-fails-closed.md) | `SEND_MODE` defaults to test; going live is an explicit switch | Accepted |
