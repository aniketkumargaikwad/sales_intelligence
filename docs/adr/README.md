# Architecture decision records

One file per decision. Status is `Proposed` until the operator approves the design, then
`Accepted`. A later ADR can supersede an earlier one; we never rewrite an accepted ADR's decision.

| # | Decision | Status |
|---|---|---|
| [0001](0001-licence.md) | MIT licence; AGPL tools only as separate services | Proposed |
| [0002](0002-database.md) | New Supabase project, plain-SQL migrations that also run on plain Postgres | Proposed |
| [0003](0003-scheduler.md) | GitHub Actions cron with windowed send runs | Proposed |
| [0004](0004-dashboard-and-public-endpoints.md) | Next.js web app for dashboard + always-on public endpoints | Proposed |
| [0005](0005-llm-access.md) | Anthropic API via the SDK behind one `generate_json`, with a cost meter | Proposed |
| [0006](0006-logic-less-templates.md) | Logic-less Mustache templates shared by engine and dashboard | Proposed |
| [0007](0007-send-mode-fails-closed.md) | `SEND_MODE` defaults to test; going live is an explicit switch | Proposed |
