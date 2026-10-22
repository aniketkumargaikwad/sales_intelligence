# ADR-0002: Database

Status: Accepted (design PR #1 merged 2026-10-22). Date: 2026-10-22.

## Context

The brief asks for Postgres, Supabase free tier to start, and plain Postgres must also work.
calling-agent-2 already has a Supabase project with VoiceSync's prospects, messages and events.
We need row-level security by `offer_id` and role, and DB-level guarantees (append-only
suppression, no send without approval).

## Decision

1. **A new Supabase project** for sales-intelligence. VoiceSync data is imported once with
   `si import` in phase 8; calling-agent-2's project is left untouched until cutover.
2. **Plain SQL migrations** in `db/migrations/NNNN_name.sql`, applied by `python -m si migrate`,
   tracked in a `schema_migrations` table. No ORM, no Supabase-only migration tooling.
3. **Portable RLS**: policies call `auth.uid()`. On Supabase that exists; on plain Postgres
   migration `0000` creates a shim `auth.uid()` that reads the `request.jwt.claim.sub` setting.
4. **Integrity in the database**, not just Python:
   - trigger: `suppression` rejects UPDATE and DELETE;
   - trigger: `messages` can't move to `sending`/`sent` without `approved_by` and `approved_at`;
   - check constraints on status values; foreign keys everywhere; `offer_id` NOT NULL.
5. **Access**: the engine (Actions) and the web app's server code use the service role; the
   browser uses the anon key + user JWT under RLS.
6. **Keep-alive** query daily (free tier pauses after inactivity) and a nightly encrypted
   `pg_dump` (free tier has no point-in-time recovery).

## Alternatives

- **New schema in the existing calling-agent-2 project**: one fewer project, but shared auth
  users, shared limits, and a risk that a migration here breaks VoiceSync's live app.
- **SQLite (Harvey-style)**: simplest locally, but GitHub Actions runners are ephemeral and the
  web app needs a shared, always-on database.
- **Neon / self-hosted Postgres**: viable; Supabase adds Auth, which the dashboard needs.

## Consequences

- Two Supabase projects for the operator during migration (the free plan allows two active projects; *verify*).
- Free-tier storage (≈500 MB, *verify*) is plenty for facts and messages at this volume; raw HTML
  of crawled pages is not stored, only extracted facts and source URLs.
