# ADR-0004: Dashboard and public endpoints

Status: Proposed (pending operator answer to brief §11 Q2 and Q8). Date: 2026-10-22.

## Context

We need an approval queue with live preview, hot leads and a funnel, possibly with logins for sales
reps. Separately, some endpoints must be **public and always on**: the RFC 8058 one-click
unsubscribe (mail providers POST to it at any time), the events webhook from proof-asset sites, the
meeting-booking webhook, and instant hot-lead alerts. GitHub Actions can't receive HTTP, and a
no-build local UI on the operator's laptop is neither public nor always on.

## Decision

One **Next.js (App Router)** app in `dashboard/`:

- Dashboard pages behind **Supabase Auth** (magic link); data access with the user's JWT under RLS;
  roles from `offer_members` (`owner`, `approver`, `rep`, `viewer`). In v1 only the founder has a login.
- Public routes: `/u/[token]` (page + one-click POST), `/api/events` (HMAC), `/api/meetings`
  (provider signature). These use the service role server-side, write rows, and send alert email to
  the founder only.
- **Host: Vercel**, matching calling-agent-2, *subject to plan terms*: Vercel's Hobby plan is
  limited to non-commercial use (*verify* against current terms). If that applies, either use
  Vercel Pro (~$20/month, a big share of a $50 budget) or deploy the same app to a free host that
  allows commercial use. The app avoids Vercel-only APIs to keep that move cheap.
- The preview renders the same Mustache templates as the engine (ADR-0006).

## Alternatives

- **No-build local UI (Harvey style)**: zero hosting, but no public endpoints, no rep logins, and
  the queue is only reachable when the laptop is on. We would still need a hosted service for
  unsubscribe and webhooks.
- **Supabase Edge Functions for the public endpoints + a static dashboard**: free and commercial-OK,
  but splits the web layer into two codebases (Deno functions + a static app).

## Consequences

- One deployable web app; the engine stays a batch job.
- Unsubscribe availability depends on the web host *and* the database (see ADR-0002 keep-alive).
