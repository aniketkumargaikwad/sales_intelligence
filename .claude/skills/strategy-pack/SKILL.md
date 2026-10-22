---
name: strategy-pack
description: Write or refresh the eight strategy documents in offers/<slug>/strategy/ (ICP, personas, positioning, messaging house, objections, channel plan, funnel, 30-day launch plan) and make them pass `si strategy check`.
---

# Strategy pack

The pack is markdown, regenerated on demand and diffable in git. Later stages (scouting, fit
scoring, copy slots, call prep, the weekly analyst) read it, so it must be specific, honest and
complete. The authoritative list of documents and required sections is `PACK` in
`si/strategy/__init__.py`.

## Front matter (every document)

```yaml
---
offer: <slug>
doc: <icp|personas|positioning|messaging|objections|channels|funnel|launch>
generated_on: YYYY-MM-DD
offer_yaml_hash: "<output of: uv run python -m si strategy hash offers/<slug>>"
sources: [offer.yaml, context/interview.md]
---
```

Quote the hash. A changed offer.yaml makes the checker warn that the pack is stale.

## Documents

| File | Sections (`## ...`) | Notes |
|---|---|---|
| `01-icp.md` | Who buys, Must have, Nice to have, Disqualifiers, Signals to watch, Where to find them | Use `icp-builder` |
| `02-personas.md` | Decision maker, Day-to-day user, What they care about, What they fear | Real roles in this segment |
| `03-positioning.md` | For, Who struggle with, We are, Unlike, Because, Alternatives they use today | One sentence each, then detail |
| `04-messaging-house.md` | Core message, Pillars, Proof we can use, Things we never say, Sample lines | Proof = only offer.proof |
| `05-objections.md` | Objections | Use `objection-bank` |
| `06-channel-plan.md` | Allowed channels, Forbidden channels, Sequence outline, Manual openers | Respect channels + compliance |
| `07-funnel.md` | Stages, Conversion targets, What we measure | Targets are (assumption) until measured |
| `08-launch-30-days.md` | Week 1, Week 2, Week 3, Week 4, Decisions needed | Tie to daily_new_prospects and budget |

## Honesty rules the checker enforces

- Any money amount must be one of `offer.price`'s amounts, unless the line is marked
  `(assumption)`, `(estimate)` or `(to verify)`, or links a source.
- Any percentage needs a source link or one of those marks on the same line.
- With `offer.proof` empty, no "trusted by", "our customers include", "clients like", etc.
- Lines starting with `>` are sample copy: no "free", "guaranteed", "urgent", "risk-free",
  "100%", "#1", and no "Re:"/"Fwd:".

## Finish

Run `uv run python -m si strategy check offers/<slug>` until it reports no errors. Then summarise
for the operator in plain language and list the decisions they need to make.
