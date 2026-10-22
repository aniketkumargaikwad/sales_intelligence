---
offer: uk-webdesign-test
doc: funnel
generated_on: 2026-10-22
offer_yaml_hash: "60a51fc02f83"
sources: [offer.yaml, context/README.md]
---

# Funnel: Northlight Studio

## Stages

1. **Sourced**: a clinic in a target segment, with a website.
2. **Qualified**: passes must-haves (independent, Ltd/LLP, auditable site), no disqualifiers.
3. **Audited**: audit built (proof asset).
4. **Contacted**: step 1 approved and sent.
5. **Engaged**: opened the audit page or replied.
6. **Call booked**: content or scoping call in the calendar.
7. **Won**: deposit paid (£900 deposit).
8. **Launched**: site live; referral ask two weeks later.

## Conversion targets

All targets are (assumption) until four weeks of data exist; the weekly report replaces them
with measured rates.

| From → to | Target |
|---|---|
| Sourced → Qualified | 40% (assumption) |
| Contacted → Engaged | 25% (assumption) |
| Engaged → Call booked | 20% (assumption) |
| Call booked → Won | 30% (assumption) |

At 5 new prospects a day and 20 working days, that is about 100 contacted a month. The targets
above would mean roughly 1–2 wins a month (assumption: arithmetic on the targets above).

## What we measure

- Counts per stage per week, per segment.
- Audit page views per contacted clinic (from the events webhook).
- Reply rate and reply intent mix (interested / question / not now / unsubscribe).
- Cost per stage, from the cost meter, against the $30 monthly budget.
- Unsubscribe and bounce rates. The kill switch trips above a 3% bounce rate (design §5.9).
