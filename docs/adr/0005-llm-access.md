# ADR-0005: LLM access

Status: Accepted (design PR #1 merged 2026-10-22). Date: 2026-10-22.

## Context

The operator chose Anthropic as the default provider (brief §4). LLMs are for judgment only:
fit reasons, dossiers, copy slots, reply intent. Inputs include attacker-controlled text (websites,
reviews, replies). Free tiers run out, and the budget is small. The brief notes that Harvey shells
out to the `claude` CLI on a subscription and asks us to check terms; we use the API instead.

## Decision

- **Anthropic API via the official Python SDK** (`anthropic`), behind a single
  `si.llm.generate_json(task, schema, trusted, untrusted, tier, offer_id)`.
- Tiers: `judgment` → `claude-opus-5-5` (strategy, dossiers, copy slots);
  `bulk` → `claude-haiku-5-5` (reply intent, fit triage, lint second opinion, injection screen).
  Effort is set explicitly per task. Gemini free tier is the fallback provider only.
- **Structured outputs** constrained to the task's Pydantic schema and validated again locally.
- **Untrusted text** goes only in the user turn, in delimited data blocks, after an injection
  screen; never in the system prompt. Model output can only fill slots or choose labels.
- **Cost meter**: per-call usage × dated price table → `costs`; daily soft and monthly hard budget
  per offer; exceeding the hard budget pauses LLM work for that offer and alerts the operator.
- **Prompt caching** for the stable prefix (offer context, rules, templates); **Message Batches** for
  large non-urgent jobs.
- Refusals are recorded and the item is skipped.
- Interactive strategy work happens in the operator's Claude Code session and is committed as
  markdown; the engine's API path is for unattended work.

## Alternatives

- **Shelling out to `claude` CLI** (Harvey): reuses a subscription, but subscription terms are not
  meant for unattended automated backends; no per-offer cost metering.
- **Multi-provider gateway (LiteLLM etc.)**: more moving parts than two providers need.

## Consequences

- Requires a funded API key; `si check` proves it with a real 1-token call.
- Model ids and prices live in config, so a model change is a config change plus an eval run.
