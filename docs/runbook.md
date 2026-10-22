# Runbook

Workflows humans follow. (Skills Claude executes live in `.claude/skills/`.)

## First-time setup

1. **Install**: `uv sync` (Python 3.12 is installed automatically by uv).
2. **Database**: create a new Supabase project (ADR-0002). Copy the connection string from
   *Project settings → Database → Connection string (URI)* into `.env` as `SI_DATABASE_URL`.
3. **Schema**: `uv run python -m si migrate`.
4. **AI**: add a funded Anthropic API key as `SI_ANTHROPIC_API_KEY`. Optional free fallback:
   `SI_GEMINI_API_KEY`.
5. **Mailbox** (needed from phase 6, checked now): `SI_SMTP_*` and `SI_IMAP_*`.
6. **Check**: `uv run python -m si check`. Everything you configured should say `ok`; things you
   haven't set up yet say `--` (not configured), which is fine.

## GitHub Actions

Add these under *Settings → Secrets and variables → Actions*:

| Name | Kind | Used by |
|---|---|---|
| `SI_DATABASE_URL` | secret | keepalive, check, migrate |
| `SI_ANTHROPIC_API_KEY` | secret | check (later: daily, send) |
| `SI_GEMINI_API_KEY` | secret (optional) | check |
| `SI_SMTP_PASSWORD`, `SI_IMAP_PASSWORD` | secrets | check (later: send, replies) |
| `SI_SMTP_HOST`, `SI_SMTP_PORT`, `SI_SMTP_USER`, `SI_IMAP_HOST`, `SI_IMAP_PORT`, `SI_IMAP_USER` | variables | check |
| `SI_ONLY_TO` | variable | test-mode allow-list |

Workflows:

- **ci**: every push and PR: lint, types, tests against a real Postgres, secret scan.
- **keepalive**: daily database round trip so the Supabase free tier doesn't pause. Skips until
  `SI_DATABASE_URL` exists.
- **check** (manual): runs `si check` with the repository's secrets.
- **migrate** (manual): applies pending migrations to the project database.

## Local development

```bash
cp .env.example .env            # then fill it in
uvx pre-commit install          # optional: gitleaks + ruff before each commit
SI_TEST_DATABASE_URL=postgresql://postgres@localhost:5432/postgres uv run pytest -q
```

The test suite creates a throwaway database on that server, applies the migrations, and drops
it at the end. Without `SI_TEST_DATABASE_URL` the database tests are skipped.
