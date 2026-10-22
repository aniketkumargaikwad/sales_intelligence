# sales-intelligence: phased plan

Status: **draft for operator review**. Follows brief §9; design in [`design.md`](design.md).
Each phase is one or more PRs, ends with tests green and a short demo to the operator, and does not
start until the previous phase's demo is accepted.

Critical path to retiring calling-agent-2's outreach engine: **1 → 3 → 5 → 6 → 7 → 8**.
Phases 2, 4, 9, 10 and 11 add value but don't block the cutover.

---

## Phase 0: Design (this PR)

- `docs/design.md`, `docs/adr/0001–0007`, this plan, `docs/brief.md`.
- **Exit**: operator answers brief §11 and approves the design; ADRs move to `Accepted`.

## Phase 1: Skeleton

- Repo layout (design §4), root `pyproject.toml` (uv, Python 3.12), ruff, mypy, pytest.
- `CLAUDE.md` v1, `.claude/settings.json`, hooks: secret-write block, "no send outside the engine",
  suppression-edit block, MCP write log.
- `si.config`: env settings + `offer.yaml` Pydantic schema with clear validation errors.
- Provider registry + protocols + fake providers for tests.
- `db/migrations/0000–0003`: auth shim, all tables from design §6, RLS, the suppression and
  approval triggers. `si migrate`.
- LLM layer: `generate_json`, price table, cost meter, budget stop, injection screen (patterns).
- `si check`: DB, live 1-token Anthropic call, SMTP/IMAP login, DNS (SPF/DKIM/DMARC), each enabled
  provider, plain-language table, exit codes.
- CI: tests against a Postgres service container, gitleaks, lint. `keepalive.yml`.
- **Acceptance**: `si migrate && si check` on a fresh Supabase project and on plain Postgres;
  trigger tests prove a message can't be sent without approval and suppression can't be edited.

## Phase 2: Offer intake + strategy pack

- `/onboard-offer` (interview + reads the website) → `offers/<slug>/offer.yaml` + `context/`.
- `/build-icp`, `offer-intake`, `icp-builder`, `objection-bank` skills; strategy markdown in
  `offers/<slug>/strategy/` (ICP, personas, positioning, messaging house, objections, channel plan,
  funnel, 30-day plan).
- Offers: `voicesync` and the second test offer (default: UK web-design agency).
- **Acceptance**: both offers produce sensible packs the operator signs off; evals for intake/ICP.

## Phase 3: Source → enrich → verify → fit

- Discovery: Places API (New) within free caps, CSV import, Maps scraper behind opt-in.
- Crawl: robots-aware `httpx_basic` + crawl4ai; regex extraction first, LLM second.
- Verify: syntax/MX/disposable (always), Reacher (when a port-25 host exists), MillionVerifier (optional).
- Dedupe keys, facts with provenance, deterministic fit score + LLM-written reason, confidence.
- UK: Companies House lookup for recipient type.
- `daily.yml` runs `source/enrich/verify/score`.
- **Acceptance**: 50 accounts per test offer, a cost report, a query proving no fact lacks a
  source URL, and fit reasons the operator agrees with on a 10-account spot check.

## Phase 4: Signals + dossiers

- Signal library (`si/signals/library.yaml`) with decay half-lives; operator confirms signals per offer.
- Collectors: JobSpy hiring, Places review changes, site diff, news search.
- `account-dossier` skill + engine task: one cited page per account above the dossier gate.
- **Acceptance**: dossiers where every sentence traces to a fact; re-scoring after a new signal.

## Phase 5: Drafting in cages

- Shared Mustache frame + step templates (HTML + text, one link + unsubscribe), renderer fixtures
  shared with the dashboard.
- `sequence-writer` skill: slot filling with `fact_ids`; honesty, data and compliance gates; lint.
- Compliance rules v1: India + UK (design §7) and `docs/compliance-matrix.md` with checked-on dates.
- Dashboard v1: login, approval queue with live preview, lint reasons, approve/edit/reject, test-mode banner.
- **Acceptance**: a gate test suite with known-bad drafts (fake price, invented customer, a
  detail not in facts, two links, non-Latin text, fake "Re:") that are all blocked; queue demo.

## Phase 6: Sending

- SMTP (Zoho/Google Workspace) and Graph (M365) mailers; mailboxes, warm-up ramp, caps,
  recipient-timezone windows, jittered spacing, threading.
- `SEND_MODE` test/live (ADR-0007), held messages, `/go-live`, `/kill-switch`, automatic pauses.
- Web app public routes: `/u/[token]` page + RFC 8058 one-click POST → suppression.
- Bounce parsing; `send.yml` windowed cron; Sent-folder reconciliation for crashed runs.
- **Acceptance**: in test mode, a real approved sequence reaches only the allow-list; everything
  else is held; one-click unsubscribe works from Gmail; kill switch stops the next run.

## Phase 7: Replies + hot leads

- IMAP triage: deterministic rules, injection screen, Haiku intent classes (design §5.12).
- Sequence stop on reply; reply drafts into the queue; temperature; instant founder alert.
- `/api/meetings` (Cal.com/Calendly) matched to leads.
- **Acceptance**: an eval set of real-shaped replies (incl. injection attempts and hostile replies)
  classified to target accuracy; alert arrives within a minute of a callback request.

## Phase 8: Proof-asset adapters + events webhook (VoiceSync first)

- `http_adapter` with HMAC both ways; `/api/events`; adapter health checks in `si check`.
- Needs access to the calling-agent-2 repo: VoiceSync `/proof-assets` and `/health` endpoints,
  events posted from `/demo` and `/for/<slug>`.
- `si import` of VoiceSync prospects, messages, events, suppression and segment profiles.
- **Cutover**: turn off calling-agent-2's outreach workflow only after one approved test sequence
  has run end-to-end in test mode on the new engine.

## Phase 9: Closer + onboarding seats

- `/call-prep`, `/proposal` (quotes from `offer.price` only), onboarding kit, first-value milestone,
  referral ask after first value.

## Phase 10: Analyst

- Weekly report (funnel, cost per stage and per meeting, copy-variant stats, what to change,
  decisions needed) in `offers/<slug>/outputs/`.
- Recommendations open a PR against `offers/<slug>/`; the operator merges.

## Phase 11: Plugin packaging + docs

- `.claude/` + `.mcp.json` packaged as the `sales-intelligence` plugin; runbook, provider matrix.
- **Acceptance**: install into a fresh repo and run `si check` in under 10 minutes.

---

## What the operator needs to provide, and when

| When | Item |
|---|---|
| Phase 1 | New Supabase project (URL + service key as GitHub secrets), funded Anthropic API key |
| Phase 3 | Google Cloud project with Places API (New) and billing enabled (free caps still apply); Companies House API key (free) |
| Phase 5 | Web host decision (Vercel plan question, ADR-0004) |
| Phase 6 | Sending domain with SPF/DKIM/DMARC, mailbox credentials, postal address for the footer |
| Phase 8 | Access to the calling-agent-2 repo and its Supabase export |
