# sales-intelligence: design

Status: **accepted** 2026-10-22 (PR #1). The §11 questions were accepted on the defaults in §16.
Date: 2026-10-22. Source brief: [`docs/brief.md`](brief.md). Decisions: [`docs/adr/`](adr/).
Build order: [`docs/plan.md`](plan.md).

Section numbers like "brief §6" point into the brief.

---

## 1. What we are building, in one paragraph

A self-hosted "sales team in a repo". The operator describes an offer once (`offers/<slug>/offer.yaml`).
A deterministic Python engine, run on a schedule, finds accounts that fit, records every fact it
learns with a source URL, scores fit, builds a per-prospect proof asset through the offer's adapter,
drafts outreach by filling a few slots in fixed templates, lints it, and puts it in an approval
queue. Nothing leaves until a human approves it, and even then a test-mode switch, a compliance gate
and kill switches sit between the queue and the mailbox. Replies are triaged, hot leads alert the
founder instantly, and a weekly analyst report proposes changes as a PR. Claude Code is the
operator's cockpit: it does the judgment-heavy interactive work (strategy, research review, call
prep, proposals) and drives the engine through slash commands.

## 2. Goals and non-goals

**Goals**

1. Industry- and country-agnostic: everything specific to an offer is data in `offers/<slug>/`.
2. Honest by construction: prices, customer names and facts in copy can only come from approved
   sources, enforced in code and tested.
3. Safe by default: approval required, test mode on unless deliberately switched off, unknown
   country or channel means "do not send".
4. Free-first: runs at $0 infrastructure with graceful degradation when a provider is missing.
5. Unattended: daily and hourly runs without a laptop open.
6. Multi-offer from day one (`offer_id` on every row).
7. VoiceSync can move off calling-agent-2's outreach engine without losing data or its demo pages.

**Non-goals (v1)**

- Not a CRM. A Postgres pipeline is enough; HubSpot/Twenty/Attio sync is optional, later.
- No cold calls, cold SMS or cold WhatsApp, ever (brief §1.12, §7).
- No automated LinkedIn or other social-network actions; the system drafts manual openers only.
- No scraping behind logins, no CAPTCHA bypass.
- No visual workflow builder (n8n etc.).

## 3. System context

```
                      ┌────────────────────────── operator's laptop ───────────────────────────┐
                      │  Claude Code + this repo (CLAUDE.md, agents, skills, commands, hooks)   │
                      │   /onboard-offer /build-icp /review-queue /call-prep ... → python -m si │
                      └──────────────┬───────────────────────────────────────────┬──────────────┘
                                     │ git push (offers/, strategy/)              │ SQL / si CLI
                                     ▼                                            ▼
┌──────────── GitHub ────────────┐        ┌───────────────── Postgres (Supabase) ─────────────────┐
│ repo + Actions cron            │        │ offers, accounts, people, facts, signals, fit_scores, │
│  daily: source/enrich/draft    │──SQL──▶│ dossiers, proof_assets, messages, events, suppression,│
│  hourly (windows): send/replies│        │ mailboxes, costs, runs, settings   (RLS by offer_id)  │
│  weekly: report → PR           │        └───────────────▲───────────────────────▲───────────────┘
└──────┬───────────────┬─────────┘                        │                       │
       │SMTP/IMAP      │HTTPS                             │ SQL (service role,    │ supabase-js +
       ▼               ▼                                  │ server-side only)     │ user JWT (RLS)
  operator's      providers: Places, crawl4ai,   ┌────────┴───────────────────────┴──────────────┐
  mailboxes       Reacher, JobSpy, Exa, LLMs     │ Web app (Next.js, Vercel)                      │
  (Zoho/GWS/M365) proof-asset adapters ◀────────▶│  /dashboard  approval queue, hot leads, funnel │
       │                                         │  /u/<token>  unsubscribe page + RFC 8058 POST  │
       ▼                                         │  /api/events HMAC webhook from adapters/sites  │
   prospects ────── click unsubscribe ──────────▶│  /api/meetings Cal.com / Calendly webhook      │
   prospects' views of /for/<slug> (adapter) ───▶│  hot-lead alert email to the founder           │
                                                 └────────────────────────────────────────────────┘
```

Three runtimes, one database:

| Runtime | Runs | Why there |
|---|---|---|
| **Engine** (`si/`, Python 3.12) | All pipeline tasks, all sending to prospects | Deterministic, tested, scheduled by GitHub Actions ([ADR-0003](adr/0003-scheduler.md)) |
| **Web app** (`dashboard/`, Next.js) | Dashboard, unsubscribe, webhooks, instant alerts | Must be always on; Actions cannot receive HTTP ([ADR-0004](adr/0004-dashboard-and-public-endpoints.md)) |
| **Claude Code** (operator's session) | Strategy, research review, call prep, proposals, queue review | Judgment work, interactive, uses the operator's own session |

The only component that ever emails a prospect is the engine's `send` task. The web app sends
mail only to the operator (alerts). Claude Code never sends; hooks block it, and it has no SMTP
credentials.

## 4. Repository layout

```
CLAUDE.md                      operating manual (roles, rules, where things live, guardrails)
.claude/
  agents/                      one subagent per seat (strategist.md, scout.md, … analyst.md)
  skills/<name>/               SKILL.md + scripts + evals/ (offer-intake, icp-builder, …)
  commands/                    /onboard-offer /build-icp /map-market /find-leads /research
                               /draft-sequence /review-queue /triage-replies /call-prep
                               /proposal /weekly-report /go-live /kill-switch
  hooks/                       pre-tool gates (see §11)
  settings.json
.mcp.json                      optional MCP servers, all disabled unless enabled per offer
offers/<slug>/
  offer.yaml                   the Offer Brief (brief §2), validated by si.config
  context/*.md                 website notes, interview answers, competitor notes
  strategy/*.md                ICP, personas, positioning, messaging house, objections, channels,
                               funnel, 30-day plan (regenerated on demand, diffable)
  templates/                   optional per-offer overrides of the shared email frame
  outputs/YYYY-MM-DD-*.md      dated reports and exports
si/                            the engine package (python -m si <task>)
db/migrations/NNNN_*.sql       plain SQL, applied by `si migrate`
dashboard/                     Next.js app (own package.json)
templates/email/               shared Mustache frame + step templates (ADR-0006)
evals/<skill>/                 golden cases for every LLM-backed step
tests/                         pytest (unit, gate, integration against a throwaway Postgres)
docs/                          design, plan, ADRs, runbook, compliance-matrix, provider-matrix
.github/workflows/             ci.yml, daily.yml, send.yml, weekly.yml, keepalive.yml, evals.yml
```

The engine package sits at the repo root (`si/`) rather than under `engine/` so that
`python -m si` works from the root with a single root `pyproject.toml` (uv).

## 5. Engine design

### 5.1 Package map

```
si/
  __main__.py, cli.py          python -m si <task> [--offer slug] [--target N] [--dry-run]
  config/                      Settings (env), OfferConfig (offer.yaml → Pydantic), loaders
  db/                          asyncpg pool, migration runner, typed repositories per table
  registry/                    Provider protocols, registry, fallback chains, health checks
  providers/
    discovery/                 places_api, gmaps_scraper, csv_import, exa_company
    crawl/                     httpx_basic, crawl4ai, firecrawl
    verify/                    syntax_mx (always), reacher, millionverifier
    signals/                   jobspy_hiring, places_reviews, site_diff, news_search
    research/                  exa, brave
    llm/                       anthropic, gemini
    mail/                      smtp, imap, graph (M365)
    proof/                     http_adapter (brief §8), none
    meetings/                  calcom, calendly (parsing only; webhooks land in the web app)
  pipeline/                    one module per task: map, source, enrich, verify, score, signals,
                               dossier, proof, draft, send, replies, report, check, stats, migrate
  gates/                       spend, data, honesty, compliance, approval, test_mode, kill_switch
  compliance/rules/*.yaml      country × channel rules with checked_on dates and sources
  scoring/                     fit scoring, dedupe keys
  llm/                         generate_json, injection screen, cost meter
  render/                      Mustache rendering of email frames (same templates as dashboard)
  audit.py                     writes runs/events rows for every write and outbound action
```

### 5.2 Provider registry

Every external capability is a `Protocol` (e.g. `Discovery`, `Crawler`, `EmailVerifier`,
`LLM`, `Mailer`, `ProofAdapter`). Implementations register with a name, a cost model and a
`configured()` check. Each offer lists a fallback order:

```yaml
providers:
  discovery: [places_api, gmaps_scraper, csv_import]
  crawl: [crawl4ai, httpx_basic]
  verify: [reacher, syntax_mx]
  llm: [anthropic, gemini]
```

Rules:

- A provider that is not configured is skipped with a log line `skipping places_api: not configured`;
  if the whole chain is unconfigured the task exits 0 with a clear summary (brief §1.8).
- A provider error falls through to the next one; the run records which one served each item.
- `si check` performs a *real* minimal call per enabled provider (a 1-token LLM completion, an
  SMTP/IMAP login, a DB round trip, one Places lookup, a Reacher check on a known address) and
  prints a plain-language table: working / not configured / failing (and why).
- Opt-in flags guard risky providers: `gmaps_scraper` (Google ToS risk) requires
  `providers.allow_scraper: true` in offer.yaml.

### 5.3 Tasks, idempotency and "target total" semantics

Each task reads the database, does bounded work, and writes results plus one `runs` row
(task, offer, started/finished, counts, cost, provider usage, error). Tasks are idempotent:

- `source --target 50` means "make sure segment X has 50 accounts", not "add 50 more".
- Per-item stage columns (`accounts.stage`, `messages.status`) make every task resumable after a
  crash; work is claimed with `SELECT … FOR UPDATE SKIP LOCKED` so overlapping runs can't double-process.
- Every task supports `--dry-run` and `--offer`.

Task list (brief §4 plus two): `onboard, map, source, enrich, signals, proof, draft, send,
replies, report, check, stats` + `migrate` (DB migrations) and `import` (VoiceSync data, CSV).

### 5.4 Pipeline and ordering

```
offer.yaml ─▶ map ─▶ source ─▶ dedupe ─▶ enrich ─▶ verify ─▶ score ─▶ signals ─▶ dossier
   ─▶ proof ─▶ draft ─▶ lint ─▶ [HUMAN APPROVAL] ─▶ send ─▶ replies ─▶ alert ─▶ meeting
   ─▶ call prep ─▶ proposal ─▶ close ─▶ onboarding ─▶ referral ─▶ analyst ─▶ (PR to offers/)
```

Fit score orders everything downstream (brief §1.7). Spend gates sit at each paid step:

| Step | Default gate (per offer, configurable) |
|---|---|
| Paid enrichment / paid verification | fit ≥ 40 and confidence ≥ medium |
| LLM dossier | fit ≥ 55 |
| Proof asset | fit ≥ 65 and a verified contact exists |
| LLM drafting | fit ≥ 65, dossier present, proof asset present (or adapter = none) |

Daily caps from offer.yaml (`daily_new_prospects`) limit how many accounts advance to draft per day.

### 5.5 Dedupe and fit scoring (deterministic)

- **Account key**: registrable domain (via public-suffix list) when known; otherwise
  normalised name + E.164 phone + rounded lat/lng. Merges keep all facts and all source URLs.
- **Person key**: lower-cased email; role addresses (`info@`, `reception@`) are flagged as such.
- **Fit score (0–100)** from the ICP in offer.yaml:
  - `disqualifiers` → hard drop (score 0, reason recorded).
  - `must_have` → each must be *evidenced by a fact*; unknown caps the score at 50 and marks
    "needs research" rather than dropping.
  - `nice_to_have` → weighted points (weights in offer.yaml, default equal).
  - `signals` → boost with exponential decay by age (half-life per signal in the signal library).
  - **Confidence** (low/medium/high) is computed from fact coverage and freshness and acts as a
    spend gate, not part of the score (idea from OpenOutreach).
- The LLM never computes the score. It writes the plain-language **reason** ("Takes bookings by
  phone (site, 2026-10-20); 4.6★ from 212 reviews (Places, 2026-10-21); no website chat") from the
  facts that produced the score, so the operator can read and disagree with it.

### 5.6 Facts and provenance

Every observation is a row in `facts`:
`(offer_id, entity_type, entity_id, key, value jsonb, source_url, source_kind, confidence,
observed_at, expires_at, run_id)`. Facts are append-only; the "current" value is the newest
non-expired row per key. Nothing reaches copy, a dossier or a score without a fact row.
Crawling reads robots.txt first and records a `robots_disallowed` fact when it must stop.

### 5.7 LLM layer

One entry point: `llm.generate_json(task, schema, *, trusted, untrusted, tier, offer_id)`.

- **Provider**: Anthropic API via the official Python SDK, not the `claude` CLI ([ADR-0005](adr/0005-llm-access.md)).
  `claude-opus-5-5` for strategy, dossiers and copy slots; `claude-haiku-5-5` for bulk
  classification (reply intent, fit triage, lint second opinion, injection screen).
  Gemini free tier is a fallback only.
- **Structured output**: responses are constrained to the Pydantic schema
  (`output_config.format` / `messages.parse`), validated again on our side; invalid → retry
  once → fail the item, never the run.
- **Untrusted text** (websites, reviews, replies) never goes in the system prompt. It is passed in
  the user turn inside clearly delimited, quoted data blocks, after a screen for injection patterns
  (deterministic patterns first, Haiku classifier second). Model output is data: it can fill slots
  or pick an intent label, it can never trigger a send, a suppression change or a tool call.
- **Cost meter**: token usage × the model's price table (kept in `si/llm/prices.yaml`, dated) is
  written to `costs` per call. Before each call the meter checks today's spend for the offer
  against `monthly_budget_usd / days_in_month` (soft) and the monthly total (hard). Exceeding the
  hard limit sets the offer's `llm_paused` flag: stop the world, alert, exit 0.
- **Cheaper paths**: offer context and templates go first in the prompt so prompt caching applies;
  non-urgent bulk work (dossiers, fit reasons) can go through the Message Batches API (half price,
  asynchronous) when the day's batch is large.
- **Refusals** (`stop_reason == "refusal"`) are recorded and the item is skipped, not retried in a loop.

### 5.8 Drafting in cages

- **Email 1** = a fixed, branded, single-column HTML frame (tables + inline CSS, phone-first) with
  a text part saying the same thing, exactly **one** link (the proof asset / know-more page) plus
  the unsubscribe link. The model fills only `subject`, `greeting` and one `scene` paragraph, and
  must return the `fact_ids` it used.
- **Follow-ups** = fixed templates in the same frame with the same slots or none.
- If a human edits a message's text in the dashboard, it goes out exactly as written, as plain text,
  with the compliance footer (identity, postal address, unsubscribe) appended by the sender.
- Templates are logic-less Mustache, rendered by both the engine and the dashboard preview
  ([ADR-0006](adr/0006-logic-less-templates.md)).

### 5.9 Gates (all in `si/gates/`, all with tests)

Each gate returns `Pass` or `Block(reasons)`; reasons are stored on the message and shown in the
dashboard in plain language. Gates run at draft time **and again at send time**.

| Gate | What it enforces |
|---|---|
| **Spend** | §5.4 thresholds; per-offer daily/monthly budget; stop-the-world flag |
| **Data** | Every `fact_id` cited exists, belongs to this account, has a `source_url`. Deterministic scan: numbers, times, money, ratings and capitalised proper nouns in slots must appear in cited facts, offer.yaml or the template; Haiku second opinion flags unsupported claims |
| **Honesty** | Prices only from `offer.price`; customer/case-study names only from `offer.proof`; banned words (free, urgent, guaranteed, … configurable); no "Re:"/"Fwd:" on first touch; script check when `copy_language: en` (reject non-Latin text); exactly one link + unsubscribe; length limits per slot and per message; no unrendered `{{tags}}`; recipient name/domain matches the account |
| **Compliance** | §7 matrix lookup for (country, channel, recipient type, consent basis); unknown → block |
| **Suppression** | Email, domain or person on the suppression list → block, always, at send time |
| **Approval** | Only `status = approved` with `approved_by` and `approved_at`; also enforced by a DB trigger |
| **Test mode** | When `SEND_MODE != live`, only addresses on the allow-list are delivered; others are `held` ([ADR-0007](adr/0007-send-mode-fails-closed.md)) |
| **Kill switch** | Global or per-offer `sending_paused`; set manually (`/kill-switch`) or automatically: bounce rate > 3% over the last 7 days (min. 20 sends), any spam complaint, or ≥ 3 negative/hostile replies in 24 h. Only a human unpauses, with a reason |

### 5.10 Message lifecycle

```
            lint/compliance fail
 drafted ─────────────────────────▶ blocked ──(edit)──▶ drafted
    │ pass
    ▼                     reject
 draft (awaiting review) ───────▶ rejected
    │ approve (who, when)
    ▼
 approved ──test mode, not allow-listed──▶ held ──(go live)──▶ approved
    │ claimed by sender
    ▼
 sending ──SMTP ok──▶ sent ──▶ (bounce event) bounced
    │ error
    ▼
 failed (retry budget) ──▶ approved | dead
 any pre-send state ──(reply / unsubscribe / bounce / kill)──▶ cancelled
```

- `Message-ID` is generated at draft time and stored. If a run dies between SMTP success and the
  DB update, the next run finds the row in `sending`, checks the mailbox's Sent folder over IMAP for
  that `Message-ID`, and marks it `sent` instead of re-sending.
- A DB trigger rejects any transition to `sending`/`sent` without `approved_by`/`approved_at`, so a
  bug in Python can't skip approval.

### 5.11 Sending and deliverability

- **Mailboxes** table: provider (smtp/graph), daily cap, warm-up start date, ramp (default
  5/day in week 1 → +5/week → cap 30/day for cold mail; configurable), health.
- **Windows**: recipient-local weekday mornings (default 09:15–11:45 in the account's timezone);
  internal test addresses skip windows (brief §1.3).
- **Spacing**: jittered 3–9 minutes between sends per mailbox inside a run.
- **Threading**: follow-ups from the same mailbox with `In-Reply-To`/`References` set to step 1's
  `Message-ID`, same subject with no fake "Re:".
- **Headers**: `List-Unsubscribe: <https://…/u/<token>>, <mailto:…>` and
  `List-Unsubscribe-Post: List-Unsubscribe=One-Click` (RFC 8058). Tokens are HMAC-signed message ids.
- **Bounces**: DSNs are parsed from IMAP; hard bounce → suppression + cancel sequence for that person.
- **Pre-flight** (`si check`): SPF, DKIM and DMARC DNS records for each sending domain; Gmail/Yahoo
  bulk-sender rules (spam rate < 0.3%) are tracked from complaints and bounces.

### 5.12 Replies and hot leads

Hourly (inside windows) the `replies` task reads each mailbox over IMAP:

1. Match to a message by `In-Reply-To`/`References`, fall back to sender address.
2. **Deterministic first**: DSN → `bounce`; `Auto-Submitted`/OOO patterns → `out_of_office`;
   explicit opt-out phrases → `unsubscribe` (suppression written immediately, no LLM needed).
3. Injection screen, then Haiku classifies the rest into: `interested, question, not_now,
   referral, unsubscribe, out_of_office, bounce, hostile, injection`.
4. Any human reply stops the sequence for that person. A reply draft goes into the approval queue
   (never auto-sent). `interested`/`question`/`referral` raise temperature and trigger an alert.

Instant events (page views, CTA opens, callback requests from the adapter's site, meeting
bookings) arrive at the web app, which writes the event and emails the founder within seconds.

### 5.13 Proof-asset adapter contract (brief §8)

```
POST {adapter_url}/proof-assets   body: {offer, prospect: {name, segment, facts[…], hours, services}}
  → 200 {asset_url, demo_url?, slug, expires_at}
POST {si_url}/api/events          body: {type: page_view|cta_open|callback_request|demo_call,
                                         slug, at, meta}
GET  {adapter_url}/health         → 200 {ok, checked_assets}
```

Both directions are signed: `X-SI-Timestamp` + `X-SI-Signature: sha256=HMAC(secret, ts + "." + body)`,
one secret per offer, 5-minute replay window, idempotency key = `slug + type + at`. Built-in
adapters: `http_adapter` (above) and `none`. Later: website-audit PDF, ROI page, mock-up.

## 6. Data model

Plain SQL migrations; every table has `offer_id` (except `users`), `created_at`, and RLS.

| Table | Purpose / key columns |
|---|---|
| `offers` | slug, name, config_hash (offer.yaml synced from git), status |
| `offer_members` | user_id, offer_id, role (`owner`, `approver`, `rep`, `viewer`) |
| `segments` | offer_id, key, industry, geography, size, target_total |
| `accounts` | offer_id, segment_id, name, domain, phone, address, country, timezone, stage, dedupe_key |
| `people` | account_id, name, role, email, email_status, is_role_address, linkedin_url, consent_basis |
| `facts` | entity_type, entity_id, key, value, source_url, source_kind, confidence, observed_at, expires_at |
| `signals` | account_id, kind, strength, observed_at, half_life_days, fact_id |
| `fit_scores` | account_id, score, confidence, reason, inputs (jsonb), version |
| `dossiers` | account_id, body_md, fact_ids[], model, cost |
| `proof_assets` | account_id, adapter, asset_url, slug, expires_at, health |
| `sequences` | offer_id, person_id, channel, template_set, state |
| `messages` | sequence_id, step, channel, status, subject, body, body_html, slots, fact_ids, lint, message_id, mailbox_id, approved_by, approved_at, sent_at, edited_by |
| `events` | offer_id, person_id/account_id, type (page_view, cta_open, callback_request, reply, bounce, unsubscribe, complaint, meeting, demo_call), meta, at |
| `replies` | message_id, raw_ref, intent, confidence, draft_message_id |
| `suppression` | value (email or domain), kind, reason, source, at — **append-only** (trigger forbids UPDATE/DELETE) |
| `mailboxes` | offer_id, address, provider, daily_cap, warmup_start, health |
| `costs` | offer_id, run_id, provider, units, usd, at |
| `runs` | task, offer_id, actor (cron/user), started_at, finished_at, counts, error |
| `settings` | scope (global/offer), key, value, set_by, reason — holds kill switches and pauses |

Suppression is global per offer and also has an `all_offers` scope for addresses that asked never
to be contacted by the operator again. Personal data is limited to what is published for business
purposes; deletion requests delete people/facts and add a hashed suppression row.

## 7. Compliance

Rules are data (`si/compliance/rules/<country>.yaml`) with a `checked_on` date and a source URL per
rule, mirrored in `docs/compliance-matrix.md` for humans. The engine evaluates
`(country, channel, recipient_type, consent_basis)` → allow/deny + required elements.
Unknown country or channel → deny.

First 90 days (pending Q7): **India** and the **UK**.

- **India**: email to business addresses published by the business itself only (the email's
  `source_url` must be the business's own site or listing); honest identity, postal address,
  one-click opt-out honoured forever, deletion on request; no cold calls, SMS or WhatsApp. DPDP
  B2B reading is untested and flagged as a risk in the matrix; the operator should get legal advice.
- **UK (PECR)**: cold email to corporate subscribers (Ltd, LLP, PLC) allowed with identity and
  opt-out; sole traders and partnerships need consent, so they are blocked by default.
  Recipient type comes from a Companies House lookup (free API) recorded as a fact; no match →
  treated as sole trader → blocked.
- **US/EU/Canada/UAE**: rules drafted but disabled until a country is enabled.

The compliance officer seat (deterministic code) owns this; LLMs never decide compliance.

## 8. Web app (dashboard and public endpoints)

Next.js (App Router) in `dashboard/`, hosted on Vercel, Supabase Auth (magic link) and RLS
([ADR-0004](adr/0004-dashboard-and-public-endpoints.md)). Plain-language UI.

- **Queue**: messages awaiting approval, ordered by fit; live preview of HTML and text parts;
  lint and compliance results with reasons; approve / edit / reject; bulk approve only within one
  segment and only for lint-clean rows.
- **Hot leads**: temperature-sorted list with the events that raised it.
- **Funnel**: stage counts, cost per stage, per-offer budget burn.
- **Controls**: kill switch, test-mode indicator (big banner while in test mode), mailbox health.
- **Public**: `/u/<token>` (unsubscribe page + one-click POST), `/api/events`, `/api/meetings`.
  These routes use no Vercel-specific APIs so the app can move to another host.

## 9. Scheduling

GitHub Actions ([ADR-0003](adr/0003-scheduler.md)):

| Workflow | Cron (UTC) | Does |
|---|---|---|
| `daily.yml` | 01:17 daily | source → enrich → verify → score → signals → dossier → proof → draft |
| `send.yml` | :07 past the hour, 03–06 and 08–11, Mon–Fri | send + replies (covers IST and UK mornings) |
| `weekly.yml` | Mon 05:23 | report → PR to `offers/<slug>/` |
| `keepalive.yml` | 00:41 daily | DB round trip so Supabase free tier doesn't pause |
| `ci.yml` / `evals.yml` | on push / on prompt changes | tests, lint, secret scan / LLM evals |

All have `workflow_dispatch` and a `concurrency` group per offer so two sends never overlap.

## 10. Claude Code layer

- **CLAUDE.md**: the operating manual: who the seats are, the honesty and compliance rules,
  where things live, "never send from Claude Code", how to run each task.
- **Agents** (`.claude/agents/`): one per seat from brief §0. Seats that are "deterministic
  code" (Compliance, Sender) get agents that *explain and operate* the engine, not replace it.
- **Commands**: brief §4 list. Each is a thin wrapper that gathers input, runs `python -m si …`,
  and summarises the result in plain language.
- **Skills**: the brief §5.3 list, each with `SKILL.md`, scripts and `evals/`. "Skills Claude
  executes" live in `.claude/skills/`; "workflows humans follow" live in `docs/runbook.md`.
- **Interactive vs unattended**: strategy packs, ICP building and market maps are produced in the
  Claude Code session and committed as markdown (cheap, reviewable). Unattended LLM work (dossiers,
  copy slots, reply triage) goes through the engine's API path with its cost meter.
- **Third-party plugins/skills** (Anthropic `sales`, marketingskills, Exa, gtm-skills) are
  installed for interactive use and mined for ideas; we vendor nothing whose licence conflicts.
- **Packaging**: phase 11 turns `.claude/` + `.mcp.json` into an installable plugin.

## 11. Security

- Secrets only in `.env` (git-ignored) and GitHub/Vercel secrets. `gitleaks` runs in a pre-commit
  hook and in CI; a Claude Code hook blocks writing files that look like keys.
- The Supabase service-role key lives only in GitHub Actions and Vercel server code. The browser
  uses the anon key + user JWT under RLS.
- **Hooks are a convenience, not the control.** Claude Code hooks block: shell commands that send
  mail outside `python -m si send`; SQL that updates/deletes `suppression`; writes containing
  secrets; and they log every MCP write. The real enforcement is in the engine and DB triggers,
  because hooks can be bypassed.
- Webhooks are HMAC-verified with replay protection; unsubscribe tokens are signed.
- All scraped and reply text is untrusted (§5.7).
- Backups: nightly `pg_dump`, encrypted with `age` before upload as a private artifact (the free
  Supabase tier has no point-in-time recovery).

## 12. Testing and evals

- **TDD** for gates, scoring, dedupe, compliance, send-window maths, warm-up ramps, state
  transitions and reply classification rules.
- **Integration tests** run against a throwaway Postgres in CI (service container) with the real
  migrations, including the DB triggers.
- **Fake providers** for every protocol so the whole pipeline runs offline in tests.
- **Evals** (`evals/<skill>/cases/*.yaml`, golden input → expected properties) for every LLM step;
  `evals.yml` runs them only when prompts, schemas or templates change, because they cost money.
- **End-to-end in test mode** before going live: one approved sequence to the allow-list,
  unsubscribe clicked, reply triaged, alert received.

## 13. Cost model (target: within `monthly_budget_usd`, default $50)

| Item | Expected |
|---|---|
| Supabase, GitHub Actions, Cal.com | $0 on free tiers (Actions minutes are free on public repos; a private repo gets 2,000 min/month, and the windowed schedule above uses well under that) |
| Vercel | $0 on Hobby **if allowed** (see risk R3), else $20/month on Pro or move the web app to a free commercial host |
| Places API | $0 within monthly free caps (verify current caps) |
| LLM | 5 prospects/day ≈ 150/month. Dossier + slots on Opus 5.5 at roughly 15k input / 2k output tokens per prospect ≈ $0.10 → ~$15/month; Haiku 5.5 triage is negligible. Measured by the cost meter, not guessed |
| Email verification | $0 with syntax/MX only; Reacher needs a host with outbound port 25 (R2) |

## 14. Risks and open issues

| # | Risk | Mitigation |
|---|---|---|
| R1 | GitHub cron runs late or is skipped at busy times; scheduled workflows are disabled after 60 days without repo activity (public repos) | Odd-minute schedules; send windows tolerate delays; weekly analyst PR keeps the repo active; `si check` reports the last successful run |
| R2 | GitHub-hosted runners likely block outbound port 25, which Reacher's SMTP checks need *(verify)* | Verifier chain: Reacher on a small host or via its SOCKS proxy option → MillionVerifier (cheap, paid) → syntax/MX only with a lower send cap for unverified addresses |
| R3 | Vercel Hobby is for non-commercial use per Vercel's terms *(verify)*; a sales engine for a business is commercial | Decide in Q2: Vercel Pro, or the same Next.js app on a free host that allows commercial use. The app avoids Vercel-only APIs |
| R4 | Supabase free tier pauses after inactivity; a paused DB breaks unsubscribe | Daily keep-alive + daily pipeline traffic; `si check` alerts if the project is paused |
| R5 | Google Maps scraping breaks or breaches ToS | Off by default; Places API first; CSV import always works |
| R6 | DPDP B2B email reading is untested | Flagged in the compliance matrix; conservative defaults; operator to get legal advice |
| R7 | calling-agent-2 is not connected to this project | Needed only for phase 8 (adapter + migration); add the repo then |

## 15. Deviations from the brief

1. **Test mode fails closed.** The brief says going live = deleting `ONLY_TO`. Here going live =
   setting `SEND_MODE=live` (one variable); if it is missing, the engine is in test mode. A fresh
   environment that forgot to set `ONLY_TO` can't send live by accident ([ADR-0007](adr/0007-send-mode-fails-closed.md)).
2. **Engine at `si/`, not `engine/si/`**, so `python -m si` works from the repo root.
3. **Two extra tasks**: `migrate` and `import`.
4. **Instant alerts come from the web app**, not the engine, because the engine only runs on cron.

## 16. Decisions pending (brief §11)

Drafted on the defaults below; each maps to an ADR or plan item and will be updated with your answers.

| # | Question | Default used in this draft |
|---|---|---|
| 1 | Licence | MIT ([ADR-0001](adr/0001-licence.md)) |
| 2 | Dashboard | Next.js; hosting depends on R3 ([ADR-0004](adr/0004-dashboard-and-public-endpoints.md)) |
| 3 | Database | New Supabase project ([ADR-0002](adr/0002-database.md)) |
| 4 | Second test offer | UK web-design agency |
| 5 | Paid data | $0; Places API within free caps only |
| 6 | LinkedIn | Manual openers only |
| 7 | First 90 days | India + UK |
| 8 | Approvers / reps | Founder only; roles exist in the schema, rep logins off |
