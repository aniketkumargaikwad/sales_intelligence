---
description: Interview the operator about an offer and write offers/<slug>/offer.yaml and context/
argument-hint: "[offer-slug] [website-url]"
---

Run the `offer-intake` skill to onboard an offer. Arguments: $ARGUMENTS

- If a slug is given and `offers/<slug>/offer.yaml` exists, this is an update: read it and the
  `context/` notes first, show what is already known, and only ask about gaps and changes.
- If a website URL is given, read it (homepage, pricing, about, contact) before asking anything,
  and record what you learned in `context/website.md` with the URLs and today's date.

Finish by running `uv run python -m si validate offers/<slug>` and fixing every problem, then tell
the operator in plain language what you wrote and what is still unknown. Suggest `/build-icp
<slug>` as the next step.
