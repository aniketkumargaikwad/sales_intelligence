---
description: Build or refresh the full strategy pack for an offer (ICP, personas, positioning, messaging, objections, channels, funnel, 30-day plan)
argument-hint: "<offer-slug>"
---

Use the `strategist` subagent to write or refresh the strategy pack for `offers/$ARGUMENTS/`,
following the `strategy-pack` skill.

Before starting, run `uv run python -m si validate offers/$ARGUMENTS`. If it fails, stop and
suggest `/onboard-offer $ARGUMENTS` instead.

When the subagent is done, run `uv run python -m si strategy check offers/$ARGUMENTS` yourself.
Report to the operator: the one-paragraph ICP, the core message, the top three objections, the
decisions they need to make, and anything marked (assumption) that they could confirm.
