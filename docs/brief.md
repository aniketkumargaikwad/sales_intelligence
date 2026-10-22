# Master prompt: `sales-intelligence`

> Paste everything below the line into Claude Code, opened in a new, empty folder that will
> become the `sales-intelligence` repo. It is written to be the brief for the whole build:
> first run, design, then build phase by phase. Research date: 21 Oct 2026. Endpoints and
> prices marked *(verify)* came from third-party roundups and must be checked against the
> vendor's own docs before use.

---

## 0. Who you are and what we are building

You are the founding engineer **and** the founding head of sales of a product called
**sales-intelligence**: a self-hosted, Claude Code–native "sales team in a repo" that takes a
description of *any* offer (product or service, any industry, any country) and runs the full
journey from "who should buy this?" to "they said yes, onboard them".

It is not a CRM, not an email blaster, not a scraper. It is the **brain and the operating
system of a small, honest, very good sales team**, which happens to use CRMs, mailboxes,
scrapers and data providers as its hands. Every capability is a pluggable provider; every
outbound action passes a human approval gate and a compliance gate enforced in code.

Think of the repo as an org chart:

| Seat | Job | Mostly |
|---|---|---|
| **Strategist** | ICP, personas, positioning, offer and pricing framing, channel choice, the playbook | LLM judgment |
| **Market Mapper** | TAM: which segments, which geographies, how many accounts, where to find them | data + LLM |
| **Scout** | Finds accounts and people that fit, dedupes, scores fit | deterministic code + data providers |
| **Researcher** | Reads each account's website, reviews, socials, news, hiring; writes a cited dossier | crawl + LLM |
| **Signal Watcher** | Watches for buying signals (hiring, new location, bad reviews, funding, tech change, job change) and re-prioritises | scheduled collectors |
| **Copywriter** | Writes sequences per channel from the dossier, in fixed templates with a few LLM slots | LLM in a cage |
| **Compliance Officer** | Per-country rules, consent basis, suppression, unsubscribe, honesty lint, injection screening | deterministic code |
| **Sender / Deliverability** | Mailboxes, warm-up, caps, send windows, bounce kill-switch, threading | deterministic code |
| **SDR (Reply Handler)** | Classifies replies, drafts answers, books meetings, hands hot leads to a human | LLM + rules |
| **Closer's assistant** | Call prep, objection handling, proposal / quote drafts, follow-up after calls | LLM |
| **Onboarding / CS** | Turns a "yes" into a started customer: checklist, kickoff, first-value milestone, referral ask | LLM + templates |
| **Analyst (RevOps)** | Funnel, cohort and copy-variant stats, cost per meeting, what to change next week | SQL + LLM |

Humans in the loop: the **founder/operator** (approves everything that leaves the building,
takes calls) and optionally **sales reps** (role-based access to the dashboard).

## 1. Where this comes from (non-negotiable lessons)

This project is extracted from a working outbound engine inside the `calling-agent-2` repo
(VoiceSync, an AI voice receptionist for Indian SMBs). That engine is live and taught us the
following. Treat each line as a requirement.

1. **Show, don't tell.** The single strongest asset was a *personalised demo built for each
   prospect before contact* (a working receptionist that already knew their timings) plus a
   personalised one-page "know more" site per prospect (`/for/<slug>`) with view tracking and a
   callback form. Generalise this as the **Proof Asset** stage: per prospect, the offer's
   adapter builds something concrete (a demo, an audit, a mockup, a sample report, a quote).
2. **Approval before anything leaves.** Everything is drafted into a queue; a human approves.
   The sender only ever reads `status = 'approved'`.
3. **Test mode is a first-class switch.** An allow-list (`ONLY_TO`) makes the sender deliver
   only to internal addresses and hold everything else, so approving a real prospect by mistake
   sends nothing. Internal test addresses skip send windows. Going live = deleting one variable.
4. **The LLM writes slots, not emails.** Email 1 is a fixed, branded, phone-first HTML template
   (tables + inline CSS, one column, one link + unsubscribe, a text part saying the same thing);
   the model fills only subject, greeting and one "scene" paragraph. Follow-ups are fixed
   templates in the same frame. This killed hallucinated prices, fake guarantees and invented
   customers. If a human edits a follow-up's text, it goes out exactly as written, as plain text.
5. **Honesty rules are lint, not vibes.** Never claim customers you don't have; only the real
   price; no "free/urgent/guaranteed"; no fake "Re:"; English-only when the operator says so
   (a script check rejects non-Latin text). Lint runs at draft time and again at send time.
6. **Deterministic first.** Ranking, fit scoring, dedupe, caps, windows, suppression and
   gating are plain code with tests. Models are for judgment (fit reasons, dossiers, copy
   slots, reply intent).
7. **Fit score orders everything** (who gets a demo, who gets drafted, queue order) so paid
   AI and paid data are never spent on weak prospects.
8. **Free-first budget, graceful degradation.** Free LLM tiers run out daily; free OpenStreetMap
   data was useless for Indian SMBs (no contacts); Google Places needs billing enabled. Every
   provider must have a fallback chain and a "skipping: not configured" path that exits 0.
   A 1-token live call (not a list-models call) is the only honest "is the key funded?" check.
9. **Unattended scheduling.** GitHub Actions cron (daily source/enrich/draft; hourly
   send + reply triage, inside each recipient's local weekday morning) worked well and costs
   nothing. Supabase free tier auto-pauses: keep a daily keep-alive.
10. **Deliverability is a product.** Sending domain with SPF/DKIM/DMARC, warm-up ramp per inbox,
    per-inbox daily caps, recipient-timezone send windows, RFC 8058 one-click unsubscribe headers,
    follow-ups threaded via `In-Reply-To` from the same inbox, jittered spacing, bounce handling.
11. **Hot leads are events.** Page views, CTA opens, callback requests and positive replies
    raise a lead's temperature and alert the founder instantly (SMTP alert + dashboard section).
12. **One business number.** All human contact routes to one number; never cold-call or cold
    WhatsApp from it (Indian TRAI rules and WhatsApp ban risk).

## 2. Inputs: the Offer Brief

The system is industry-agnostic because everything specific lives in data, not code. Build a
`/onboard-offer` command that interviews the operator (and reads their website) and writes
`offers/<offer-slug>/offer.yaml` plus `offers/<offer-slug>/context/*.md`. Schema (extend as needed):

```yaml
offer:
  name: VoiceSync
  one_liner: "An AI receptionist that answers every call 24/7 in Marathi, Hindi and English"
  type: saas | service | product | agency | marketplace
  website: https://voicesync.in
  price: { from: "₹2,499/month", upfront: "none", trial: "14-day pilot" }   # the ONLY prices copy may state
  proof: { customers: [], case_studies: [], numbers: [] }                   # empty = never claim any
  differentiators: []
  objections: [{ objection: "", answer: "" }]
  proof_asset: { adapter: voicesync_demo, description: "per-prospect demo receptionist" }
market:
  geographies: [{ country: IN, regions: [Maharashtra], timezone: Asia/Kolkata }]
  segments: [{ key: dental_mh, industry: dental, size: "1-20 staff", languages: "Marathi, Hindi or English" }]
  b2b_or_b2c: b2b
  exclude: []
icp:
  must_have: []        # e.g. "takes phone bookings"
  nice_to_have: []     # e.g. "4.3+ rating, 100+ reviews"
  disqualifiers: []
  signals: []          # chosen from the signal library, confirmed by the operator
channels:
  allowed: [email, linkedin_manual, whatsapp_manual, visit, call_inbound]
  forbidden: [cold_call, cold_whatsapp]
  copy_language: en
  tone: "confident founder, warm, a little playful, never hype"
sender:
  from_name: Aniket
  role: Founder
  business_phone: "+91 …"
  postal_address: "…"
  mailboxes: [admin@voicesync.in]
constraints:
  monthly_budget_usd: 50
  daily_new_prospects: 5
  approval: required
  test_mode_only_to: [founder@gmail.com]
```

Multiple offers can live side by side (multi-tenant from day one: every table has `offer_id`).

## 3. Outputs

Per offer, the machine produces and keeps current:

- **Strategy pack**: ICP, personas, positioning, messaging house, objection bank, channel plan,
  a funnel design (stages, conversion targets), and a 30-day launch plan. Markdown in
  `offers/<slug>/strategy/`, regenerated on demand, diffable in git.
- **Account and lead lists** with a fit score, a plain-language *reason* per lead (borrowed from
  OpenOutreach: "a verdict you can read and disagree with"), source URLs and dates for every fact.
- **Dossiers**: one cited page per account.
- **Proof assets**: per-prospect demo/audit/know-more page via the offer's adapter.
- **Sequences**: drafted per channel into the approval queue; manual-channel openers (LinkedIn,
  WhatsApp, Instagram, visit scripts) that a human sends by hand.
- **Reply drafts and meeting bookings**; **call-prep briefs**; **proposals/quotes**.
- **Onboarding kits** for new customers; **referral asks** after first value.
- **Weekly report**: funnel, cost per stage, best/worst copy, what to change, decisions needed.

## 4. Architecture

Two layers. Keep them separate.

**A. The engine (deterministic, scheduled, tested).** Python 3.12, `uv`, `httpx`, `asyncpg`,
Pydantic models, pytest. Postgres (Supabase free tier to start; plain Postgres must also work).
A provider registry: every external capability is an interface with ≥1 implementation and a
fallback order configured per offer. CLI entry: `python -m si <task>` with tasks
`onboard, map, source, enrich, signals, proof, draft, send, replies, report, check, stats`.
Scheduled by GitHub Actions (cron) with `workflow_dispatch` for manual runs. Every task is
idempotent and resumable ("target total" semantics, like OpenOutreach).

**B. The Claude Code layer (judgment, operator UX).** The repo is designed to be *driven from
Claude Code*:

```
CLAUDE.md                     # operating manual: roles, rules, where things live, guardrails
.claude/
  agents/                     # one subagent per seat in §0 (strategist.md, scout.md, …)
  skills/                     # executable skills (SKILL.md + scripts) — see §6
  commands/                   # /onboard-offer /build-icp /map-market /find-leads /research
                              # /draft-sequence /review-queue /triage-replies /call-prep
                              # /proposal /weekly-report /go-live /kill-switch
  hooks/                      # pre-tool gates: block sends outside the engine, block secrets in
                              # files, block edits to suppression list, log every MCP write
.mcp.json                     # project MCP servers (see §5), all optional, all behind flags
offers/<slug>/                # offer.yaml, context/, strategy/, outputs/ (dated filenames)
engine/ (si/)                 # the Python engine
dashboard/                    # approval queue, hot leads, funnel (Next.js or a no-build HTML UI)
docs/                         # runbook, compliance matrix, provider matrix, ADRs
```

Package the Claude Code layer as an installable **plugin** (`sales-intelligence` plugin with
its agents, skills, commands, hooks and `.mcp.json`) so another repo can install it. Separate
"skills Claude executes" from "workflows humans follow" (idea from KarlRaf/gtm-starter-kit) and
keep persistent context in the repo so no session re-explains the business.

**LLM policy.** Default provider Anthropic (operator's choice): `claude-opus-5-5` for strategy,
dossiers and copy slots; `claude-haiku-5-5` for bulk classification (reply intent, fit triage,
lint second opinions). Gemini free tier as fallback only. Every call goes through one
`llm.generate_json(schema=…)` with retries, a cost meter per offer per day and a hard budget
stop. Never put scraped or reply text in a system prompt; wrap it as quoted data and screen it
for prompt-injection before any model sees it (replies and websites are attacker-controlled).

**Data model (minimum).** `offers, segments, accounts, people, facts (observation rows with
value, source_url, confidence, observed_at — idea from Harvey), signals, fit_scores, dossiers,
proof_assets, messages (channel, step, status draft→approved→sent→failed, meta, body, body_html),
events (page_view, cta_open, reply, bounce, unsubscribe, meeting), suppression, mailboxes,
costs, runs`. Row-level security by `offer_id` and role.

## 5. Tooling: providers, MCP servers, connectors

Rule of thumb from the research: *two or three well-chosen servers beat eight*. Every server
below is optional and switched on per offer. Prefer an API/CLI provider in the engine (for
unattended runs) and the MCP server for interactive work in Claude Code.

### 5.1 Free / self-hosted core (default stack)

| Need | Pick | Notes |
|---|---|---|
| Local-business discovery | **gosom/google-maps-scraper** (MIT, Go, Docker, CSV/JSON/Postgres, REST API, visits sites for emails) | Breaks when Maps UI changes; Google ToS risk — operator must opt in. Alternative: Google Places API (New) with per-SKU free caps (verify current caps: roughly 10k Essentials / 5k Pro / 1k Enterprise events per month per SKU; Text Search Pro ≈ $32/1k after free tier *(verify)*); requesting ratings/reviews bumps the SKU tier. |
| Website reading | **crawl4ai** (LLM-ready markdown), **Firecrawl** (AGPL; hosted has keyless daily allowance) | Read homepage, contact, team, careers, robots, sitemap; regex first, LLM second. |
| Agentic browsing (rare) | **browser-use** or **Stagehand** | Only for pages that need clicks; never logins to social networks. |
| Email verification | **reacherhq/check-if-email-exists** (AGPL-3.0, Rust, Docker HTTP backend) | Run as a separate service (don't vendor AGPL code). Plus `mailchecker` for disposable domains. |
| Hiring signals | **JobSpy** (LinkedIn/Indeed/Glassdoor/ZipRecruiter job scraper) | Hiring a receptionist/sales role = strong signal for many offers. |
| Web research | **Exa** MCP (keyless tier exists; `company`/`people` categories; official company-research and people-search Claude skills), Brave Search MCP | Exa company category rejects domain/date filters. |
| CRM (optional) | Built-in Postgres pipeline first; **Twenty** (open-source CRM, native MCP on Twenty Cloud) or **HubSpot free CRM** + remote MCP `mcp.hubspot.com` (GA 13 Apr 2026, OAuth 2.1/PKCE) | Don't make a CRM a dependency of the core loop. |
| Sending | Own mailboxes over SMTP/IMAP (Zoho, Google Workspace, M365 via Graph) | The engine sends; MCP mail servers are for triage only and never send without an explicit operator OK. |
| Scheduling | GitHub Actions cron; optional Claude Code routines for weekly strategy reviews | |
| Meetings | Cal.com (self-hostable) or Calendly webhook → `events` | Match bookings back to leads. |

### 5.2 Paid data and engagement (plug in when budget allows)

| Category | Options (remote MCP where known) |
|---|---|
| All-in-one B2B data + sequences | **Apollo** `https://mcp.apollo.io/mcp` (OAuth or API key; MCP included on free plan but free accounts on personal email can't use people search/enrichment *(verify)*); Amplemarket `https://mcp.amplemarket.com/mcp` (expensive) |
| Enrichment waterfall | **Clay** (built-in Claude connector; 150+ providers; first-connect credits), FullEnrich, Lusha, LeadMagic MCP, Crustdata (people/company/jobs/posts) |
| Email finders/verifiers | Hunter, Icypeas, Findymail, Prospeo, MillionVerifier, Reoon |
| Intent/signals | PredictLeads, Crustdata, ZoomInfo GTM AI (1,000 free credits to start *(verify)*), Common Room |
| Sequencers | Instantly `https://mcp.instantly.ai/mcp` (paid plan), Smartlead `server.smartlead.ai/mcp` (SSE, mostly read), lemlist (OAuth/key; URL differs by source *(verify)*), Outreach (needs Amplify add-on) |
| CRMs | HubSpot (above), Attio `https://mcp.attio.com/mcp`, Salesforce (admin-configured), Pipedrive (no official MCP found — use API) |
| LinkedIn | HeyReach (multi-sender), Unipile (API), LinkedIn official API for posting only. **Default off**: automation on personal accounts risks bans; prefer manual openers drafted by the system. |
| WhatsApp | Meta's official WhatsApp Business Tools MCP (announced Sept 2026 *(verify repo)*) for template management on the **Cloud API** only, opt-in contacts only, approved templates outside the 24-hour window. Never unofficial WhatsApp Web automation. |
| Research | Perplexity MCP, Parallel, Tavily, Serper, DataForSEO (Business Listings ≈ $0.37/1k per Harvey *(verify)*) |
| Calls | Gong / Fireflies MCP for call notes when the operator uses them |

### 5.3 Claude Code plugins and skills to install (then fork what you need)

- **Anthropic `sales` plugin** — `claude plugin marketplace add anthropics/knowledge-work-plugins`
  then `claude plugin install sales@knowledge-work-plugins`. Account research, call prep,
  outreach drafting, competitive intel, pipeline review; connectors for Slack, HubSpot, Close,
  Clay, ZoomInfo, Notion, Fireflies, M365. Ships without prospect data — our engine is the data.
  Also look at its `marketing` and `customer-support` plugins for onboarding/CS seats.
- **coreyhaines31/marketingskills** — `npx skills add coreyhaines31/marketingskills` (cold-email,
  prospecting, copywriting, copy-editing, offers, pricing, onboarding, referrals, launch,
  sales-enablement, revops, competitors, customer-research, marketing-psychology, …). Its
  prospecting skill already encodes "public contacts only, source URL + verification date".
- **Exa** company-research and people-search skills.
- **gtm-skills/gtm** (MIT) — role/industry/methodology playbooks (MEDDPICC, SPIN, Challenger,
  Gap Selling, Sandler) and an MCP server; mine for the Closer's-assistant seat.
- **KarlRaf/gtm-starter-kit** — repo conventions: context folder, signal library, dated outputs,
  decay-aware signals, sync scripts that feed results back into scoring, a worked example.
- Skill lists to scan for more: `loootai/awesome-gtm` (agent skills section: gtm-eng-skills,
  goose-skills, google-maps-agent-skills, gtm-cheat-codes, linkedin-skills),
  `eliasstravik/awesome-gtm-engineering`, `h4ckf0r0day/awesome-ai-web-scraping`.

Write our own skills (each with `SKILL.md`, scripts, and eval cases): `offer-intake`,
`icp-builder`, `market-map`, `fit-scoring`, `account-dossier`, `signal-library`,
`sequence-writer` (slot-filling against fixed templates), `honesty-lint`, `reply-triage`,
`call-prep`, `objection-bank`, `proposal-writer`, `onboarding-kit`, `weekly-review`,
`compliance-matrix`, `deliverability-check`, `proof-asset` (adapter runner).

### 5.4 Open-source repos to study (borrow ideas; respect licences)

| Repo | Licence / size | Take this |
|---|---|---|
| **ethanplusai/harvey** | MIT, ~1.9k★ | Heartbeat loop with deterministic priority (replies → send → write → prospect → analyse); five sub-agents; SQLite `observations` with confidence + provenance; pre-send gate (unrendered merge tags, banned phrases, length, link count, recipient mismatch); bounce-rate kill switch; operator confirms which signals to collect. Note: it shells out to the `claude` CLI on a subscription — check Anthropic's terms before copying that; we use the API. |
| **eracle/OpenOutreach** | GPLv3, ~3.4k★ | Describe-the-product onboarding; per-lead plain-language verdicts; confidence as a *spend gate* not a score; discovery and sending as separate tools piped via JSON Lines; resumable target totals; "ask once" config. GPL — don't copy code into a permissive repo. |
| **xyluxx/openoutbound** | Apache-2.0, very early (1 commit) | Design reference only: one engine exposed as MCP server + skill + CLI + REST over one registry; safety gate (scopes, limits, approvals, budgets, audit) enforced in code; 15 signals + plain-English custom signals; unified multi-channel inbox; locked rules for unsubscribes, privacy requests, hostile replies and injection attempts; human takeover. |
| **JamesUgbanu/agent-sdr** | MIT | Approval workflows, controlled agentic actions, full audit trail. |
| **MatthewDailey/open-sdr** | MPL-2.0 | Research agent usable as CLI or MCP server. |
| **gosom/google-maps-scraper** | MIT, ~3.9k★ | Discovery service (see §5.1). |
| **reacherhq/check-if-email-exists** | AGPL-3.0, ~9k★ | Verification service (see §5.1). |
| **twentyhq/twenty** | open source | CRM option with MCP. |
| OpenGTM / openbower / bricks / cubex | various | Self-hosted Clay-style enrichment tables and waterfalls — compare before building our own table UI. |
| **n8n** + awesome-n8n-templates | fair-code | Only if the operator wants visual workflows; not a core dependency. |

## 6. The pipeline (stages and gates)

```
Offer Brief → Strategy pack → Market map → Source → Dedupe → Enrich → Verify → Fit score
→ Signals → Dossier → Proof asset → Draft (slots into templates) → Lint (honesty + compliance)
→ HUMAN APPROVAL → Send (caps, windows, warm-up, test mode) → Replies (classify, draft, stop
sequence) → Hot-lead alert → Meeting → Call prep → Proposal → Close → Onboarding → Referral
→ Analyst feeds results back into ICP, signals and copy
```

Gates that must exist in code, each with tests:
- **Spend gate**: no paid enrichment, proof asset or LLM drafting below a fit threshold; daily
  budget per offer; stop-the-world when exceeded.
- **Data gate**: every fact used in copy must exist in `facts` with a source URL; copy that
  names a detail not in facts is rejected.
- **Honesty gate**: prices only from `offer.price`; customer names only from `offer.proof`;
  banned words; language/script check; one link + unsubscribe; length limits.
- **Compliance gate** (§7) per recipient country and channel.
- **Approval gate**: sender reads only approved rows; approval records who and when.
- **Test-mode gate**: `ONLY_TO` allow-list holds everything else.
- **Kill switches**: `/kill-switch` pauses all sending; automatic pause on bounce rate > 3%,
  spam complaint, or a burst of negative replies.

## 7. Compliance (build a matrix, encode it, keep it current)

Ship `docs/compliance-matrix.md` and `si/compliance/` with rules per country × channel. Starting
points from the research (have the operator get legal advice; record the date each rule was
checked):

- **India**: DPDP Act 2023 + DPDP Rules 2025 (notified Nov 2025; consent duties phase in —
  sources disagree on dates, verify in the Gazette). No "legitimate interest" basis for
  marketing; a B2B reading for conspicuously published professional addresses exists but is
  untested — treat as risk. TRAI governs voice/SMS (registered headers/templates, DLT);
  enforcement is active (700k+ notices to unregistered telemarketers reported for 2025).
  Default: email to published business addresses only, honest identity, postal address,
  one-click opt-out honoured forever, purpose limitation, deletion on request; **no cold calls,
  no cold SMS, no cold WhatsApp**.
- **US**: CAN-SPAM (identity, physical address, opt-out within 10 business days, no deceptive
  subjects). **UK**: PECR — cold email to corporate subscribers (Ltd/LLP) OK with opt-out; sole
  traders/partnerships need consent. **EU**: GDPR + ePrivacy, country-specific (Germany strict).
  **Canada**: CASL (implied consent rules). **UAE**: PDPL.
- Gmail/Yahoo bulk-sender rules: SPF + DKIM + DMARC, RFC 8058 one-click unsubscribe, spam
  rate under 0.3%.
- Respect robots.txt and site terms; never bypass CAPTCHAs or log in to social networks to
  scrape; keep source URLs and dates for every personal datum; suppression list is append-only.

## 8. The adapter contract (how VoiceSync plugs in)

`sales-intelligence` must not know what VoiceSync is. VoiceSync (in `calling-agent-2`) becomes
the first **offer** plus a **proof-asset adapter** and an **events webhook**:

```
POST {adapter_url}/proof-assets        # body: prospect (name, segment, site facts, hours, services)
  → { asset_url, demo_url, slug, expires_at }        # e.g. voicesync.in/demo/<slug>, /for/<slug>
POST {si_url}/events                   # from the offer's own site: page_view, cta_open,
                                       # callback_request, demo_call {slug, at, meta}
GET  {adapter_url}/health              # daily health check test-calls/opens every asset
```

Signed with an HMAC shared secret per offer. Other offers use other adapters (website audit
PDF, Loom-style video script, mock-up, ROI calculator page, or "none").

Migration plan for the existing VoiceSync data: export `prospects`, `outreach_messages`,
`events`, suppression and segment/industry profiles from calling-agent-2's Supabase; import as
offer `voicesync`; keep calling-agent-2's `/demo`, `/for` pages and agent as the adapter; turn
off calling-agent-2's outreach workflow only after the new engine has sent one approved test
sequence end-to-end in test mode.

## 9. Build phases (each ends with tests passing and a demo to the operator)

0. **Design first.** Read this brief, ask the operator the open questions (§11), write
   `docs/design.md` and ADRs (DB, scheduler, dashboard tech, licence for our repo), then a
   phased plan. Do not write engine code before the operator approves the design.
1. **Skeleton**: repo layout, CLAUDE.md, provider registry, config, DB schema + migrations,
   `si check` (live 1-token LLM call, DB, mailbox login, each enabled provider), CI.
2. **Offer intake + strategy pack**: `/onboard-offer`, `/build-icp`, strategy markdown,
   objection bank. Acceptance: VoiceSync and one unrelated offer (e.g. a web-design agency in
   the UK) both produce sensible packs.
3. **Source → enrich → verify → fit**: Maps scraper/Places + crawl4ai + Reacher; dedupe;
   facts with provenance; fit score + reasons. Acceptance: 50 accounts for each test offer,
   cost report, no fact without a source URL.
4. **Signals + dossiers**.
5. **Drafting in cages**: branded HTML templates (shared frame, text part, one link), slot
   filling, lint, approval queue in the dashboard with live preview.
6. **Sending**: mailboxes, warm-up ramp, caps, recipient-timezone windows, threading,
   unsubscribe page + one-click header, test mode, kill switches, bounce handling.
7. **Replies + hot leads**: IMAP triage, intent classes (interested, question, not now,
   referral, unsubscribe, out of office, bounce, hostile, injection), drafts, sequence stop,
   instant alert, meeting matching.
8. **Proof-asset adapters + events webhook** (VoiceSync first).
9. **Closer + onboarding seats**: call prep, proposal/quote, onboarding kit, referral ask.
10. **Analyst**: weekly report, copy-variant stats, cost per meeting, recommendations that
    open a PR against `offers/<slug>/` (the system proposes, the operator merges).
11. **Plugin packaging + docs**: install into another repo in under 10 minutes.

## 10. Engineering rules

- TDD for gates, scoring, compliance, sending and reply classification; eval sets (golden
  inputs → expected outputs) for every LLM skill; run evals in CI on prompt changes.
- No secrets in the repo; `.env` + GitHub secrets; a hook blocks committing anything that
  looks like a key.
- Every outbound or write action is logged in `runs`/`events` with who, what, why.
- Plain-language UI copy; the operator is a founder, not a RevOps engineer.
- Small commits, conventional messages, nothing pushed to `main` without tests green.
- Prefer boring, cheap, self-hostable tech; respect the monthly budget in `offer.yaml`.

## 11. Ask the operator before designing

1. Which licence for this repo (MIT, or AGPL if we want to embed AGPL tools)?
2. Dashboard: extend Next.js on Vercel (as in calling-agent-2) or a no-build local UI (Harvey style)?
3. Database: new Supabase project or reuse the existing one with a new schema?
4. Which second offer should we use as the "not VoiceSync" test case?
5. Paid data budget per month, and which (if any) of Apollo / Clay / Places / DataForSEO to enable?
6. Is LinkedIn in scope (manual openers only, or HeyReach/Unipile)?
7. Countries for the first 90 days (drives the compliance matrix)?
8. Who besides the founder approves sends, and should sales reps get dashboard logins?

## 12. Research sources (verify before relying on any endpoint or price)

- Anthropic knowledge-work plugins: https://github.com/anthropics/knowledge-work-plugins
- Marketing skills: https://claudemarketplaces.com/skills/coreyhaines31/marketingskills/prospecting
- Sales MCP roundups: https://layrcake.dev/guides/best-mcp-servers-for-sales ,
  https://www.amplemarket.com/blog/best-mcp-servers-for-sales ,
  https://use-apify.com/blog/mcp-servers-marketing-business-2026 ,
  https://www.breakcold.com/blog/best-crms-with-mcp-server
- HubSpot remote MCP GA: https://developers.hubspot.com/changelog/remote-hubspot-mcp-server-is-now-generally-available
- Exa skills: https://exa.ai/docs/reference/company-research-claude-skill ,
  https://exa.ai/docs/reference/people-search-claude-skill
- Repos: https://github.com/ethanplusai/harvey , https://github.com/eracle/OpenOutreach ,
  https://github.com/xyluxx/openoutbound , https://github.com/JamesUgbanu/agent-sdr ,
  https://github.com/MatthewDailey/open-sdr , https://github.com/reacherhq/check-if-email-exists ,
  https://hub.docker.com/r/gosom/google-maps-scraper , https://github.com/gtm-skills/gtm ,
  https://github.com/KarlRaf/gtm-starter-kit , https://github.com/loootai/awesome-gtm ,
  https://github.com/eliasstravik/awesome-gtm-engineering
- Compliance: https://en.wikipedia.org/wiki/Digital_Personal_Data_Protection_Rules,_2025 ,
  https://www.trai.gov.in/sites/default/files/2026-09/Regulation_18092026.pdf ,
  https://protectcomply.com/blog/dpdp-consent-whatsapp-sms-email-marketing/
- WhatsApp MCP: https://thenewstack.io/meta-mcp-whatsapp-business-claude/
- Places pricing: https://developers.google.com/maps/billing-and-pricing/march-2025 ,
  https://openplacesapi.com/blog/google-places-api-pricing
