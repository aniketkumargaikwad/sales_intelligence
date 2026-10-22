---
name: icp-builder
description: Write offers/<slug>/strategy/01-icp.md, the ideal customer profile, from offer.yaml and context. Use when building or refreshing an offer's ICP, or when fit scoring needs clearer must-haves and disqualifiers.
---

# ICP builder

The ICP is the input to deterministic fit scoring (design §5.5), so write it for a machine as well
as a human: every must-have, nice-to-have and disqualifier must be something we could **observe
and cite** from public data (a website, a listing, reviews, job posts, a registry).

## Steps

1. Read `offer.yaml` (`market`, `icp`, `channels`) and `context/`.
2. For each segment, describe who buys in one concrete paragraph: size, place, how they operate
   today, what the offer replaces.
3. Turn `icp.must_have`, `nice_to_have` and `disqualifiers` into observable tests. For each, say
   **how we'd detect it** and from **which source**: "Takes bookings by phone: phone number is
   the primary CTA on their site or listing". If a test can't be observed, rewrite it or flag it.
4. Signals to watch: pick from hiring (e.g. a receptionist job post), new location, review trends,
   tech changes, ownership changes. Give each a reason it predicts buying and a rough freshness
   window (e.g. "hiring post < 30 days").
5. Where to find them: concrete sources per country (Google Places categories, registries such as
   Companies House in the UK, trade directories, associations). Note any terms-of-service risk.
6. If you propose changes to `offer.yaml`'s `icp` block, list them under a "Proposed changes to
   offer.yaml" heading; the operator decides.

## Required sections (checked by `si strategy check`)

`## Who buys`, `## Must have`, `## Nice to have`, `## Disqualifiers`, `## Signals to watch`,
`## Where to find them`.

Market sizes and percentages need a source link or an `(assumption)` mark on the same line.
