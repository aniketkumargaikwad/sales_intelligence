# sales-intelligence

A self-hosted, Claude Code–native "sales team in a repo": describe an offer once, and it finds who
should buy it, researches them with cited facts, drafts honest outreach into an approval queue,
sends only what a human approved, and turns replies into meetings and customers.

Status: **phase 1 (skeleton)**: config, database schema with its safety triggers, provider
registry, LLM layer with budget and injection guards, and `si check`. See the [plan](docs/plan.md).

```bash
uv sync
cp .env.example .env   # fill in what you have
uv run python -m si migrate
uv run python -m si check
```

Setup details: [runbook](docs/runbook.md). Working in Claude Code: [CLAUDE.md](CLAUDE.md).

- [Brief](docs/brief.md) · [Design](docs/design.md) · [Plan](docs/plan.md) · [ADRs](docs/adr/) · [Runbook](docs/runbook.md)
