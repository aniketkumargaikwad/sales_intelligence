# ADR-0003: Scheduler

Status: Proposed. Date: 2026-10-22.

## Context

The pipeline must run unattended: daily sourcing/drafting, sends and reply triage inside each
recipient's weekday morning, and a weekly report. The existing VoiceSync engine used GitHub
Actions cron successfully at no cost (brief §1.9).

## Decision

**GitHub Actions** with `schedule` + `workflow_dispatch`:

- `daily.yml` (once a day), `send.yml` (hourly, but only in UTC hours that contain a configured
  recipient-morning window, Mon–Fri), `weekly.yml`, `keepalive.yml`, plus `ci.yml` and `evals.yml`.
- Crons use odd minutes (not `:00`) because top-of-hour schedules are the most delayed.
- `concurrency: { group: send-<offer>, cancel-in-progress: false }` so runs never overlap; inside
  the engine, rows are claimed with `FOR UPDATE SKIP LOCKED` as a second guard.
- The send window is computed per recipient in Python; the cron only decides when the engine wakes.
  A late cron run simply sends fewer messages that hour.
- Service containers (Reacher, the Maps scraper when enabled) run inside the job when needed.
- Optional Claude Code routines for the weekly strategy review, which is interactive work anyway.

## Alternatives

- **Supabase `pg_cron` + Edge Functions**: always-on and close to the data, but the engine is
  Python with heavy dependencies (crawl4ai, JobSpy) that don't fit Deno edge functions.
- **A small VPS with systemd timers**: most reliable, costs ~$5/month and needs maintenance. Kept as
  the fallback if Actions scheduling proves too unreliable, and as a host for Reacher (port 25).
- **Cloudflare Workers cron**: same runtime mismatch as Edge Functions.

## Consequences

- No server to maintain; logs are in the Actions UI.
- Scheduled workflows can be delayed and are auto-disabled after 60 days without repository
  activity on public repos; the weekly analyst PR keeps the repo active and `si check` reports the
  last successful run per task.
- Private repos have a monthly minutes allowance (2,000 on Free, *verify*); the windowed send
  schedule (~8 runs/weekday) stays well inside it.
