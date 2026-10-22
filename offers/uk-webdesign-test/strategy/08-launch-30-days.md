---
offer: uk-webdesign-test
doc: launch
generated_on: 2026-10-22
offer_yaml_hash: "60a51fc02f83"
sources: [offer.yaml, context/README.md]
---

# 30-day launch plan: Northlight Studio

This is a test offer. "Launch" here means running it end to end **in test mode only**, to prove
the pipeline works for a UK agency.

## Week 1

- Source 50 physiotherapy clinics in two English towns via Places (phase 3).
- Companies House check on each; drop sole traders and partnerships.
- Spot-check 10 fit scores and reasons with the operator.

## Week 2

- Build audits for qualified clinics (needs the `site_audit` adapter, phase 8).
- Draft step 1 for the top 10 by fit; review every draft in the queue.

## Week 3

- Approve drafts in test mode; confirm everything is held except the test inbox.
- Click the unsubscribe link from a test message; confirm suppression.

## Week 4

- Weekly report on the test run: what was sourced, what qualified, cost per stage.
- Decide whether the agency shape needs any code change (it should not).

## Decisions needed

- Confirm the audit is the right proof asset for agencies, and approve building `site_audit`.
- PageSpeed threshold for "slow" (proposed: mobile score below 50).
- Whether to add the dental segment in the same test run or after physio.
