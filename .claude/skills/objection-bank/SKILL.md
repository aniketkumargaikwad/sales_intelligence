---
name: objection-bank
description: Write offers/<slug>/strategy/05-objections.md, the objection bank: what prospects say, what they mean, and an honest answer. Use when building the strategy pack, preparing call prep, or after replies reveal a new objection.
---

# Objection bank

Start from `offer.objections` (the operator's own answers win) and add the objections this
segment typically raises: price, timing, "we already have X", trust, switching cost, language,
data privacy, "send me something".

For each objection write, under `## Objections`, a `### <objection in the prospect's words>`
block with:

- **What they usually mean** (one line).
- **Honest answer** (2–4 sentences, plain language). Only our real price, only proof we may name,
  no promises we can't keep. If the honest answer is "this isn't for you", say so.
- **Proof or next step** we can offer (the proof asset, a pilot on stated terms, a call).
- **Source**: `offer.yaml`, `context/interview.md`, a reply id, or `(assumption)`.

Sample replies go in `>` block quotes and follow the outbound rules (no "free", "guaranteed",
"urgent", no fake "Re:").

When reply triage (phase 7) sees a new objection twice, add it here and open a PR.
