"""The one way the engine calls a model: `generate_json` (ADR-0005)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from si.llm.budget import Budget, Meter, decide
from si.llm.pricing import cost_usd, estimate_usd
from si.llm.types import Completion, Effort, LLMProvider, LLMRequest, Tier
from si.llm.untrusted import UNTRUSTED_RULE, Untrusted, screen, wrap
from si.registry import Registry

log = logging.getLogger("si.llm")

T = TypeVar("T", bound=BaseModel)

DEFAULT_EFFORT: dict[Tier, Effort] = {"judgment": "high", "bulk": "low"}


class BudgetExceeded(Exception):
    def __init__(self, decision: str, detail: str) -> None:
        self.decision = decision
        super().__init__(detail)


class UntrustedInputRejected(Exception):
    def __init__(self, source: str, reasons: list[str]) -> None:
        self.source = source
        self.reasons = reasons
        super().__init__(f"possible prompt injection in {source}: {', '.join(reasons)}")


class LLMRefused(Exception):
    pass


class LLMOutputInvalid(Exception):
    pass


@dataclass(frozen=True)
class OfferLLMContext:
    offer_id: UUID
    budget: Budget
    provider_order: Sequence[str]


@dataclass(frozen=True)
class Generated(Generic[T]):
    value: T
    provider: str
    model: str
    usd: Decimal


@dataclass
class LLMDeps:
    providers: Registry[LLMProvider]
    meter: Meter
    run_id: UUID | None = None


def build_prompt(
    instructions: str, trusted: str, untrusted: Sequence[Untrusted]
) -> tuple[str, str]:
    system = f"{instructions.strip()}\n\n{UNTRUSTED_RULE}"
    parts = [trusted.strip()] if trusted.strip() else []
    parts.extend(wrap(item) for item in untrusted)
    return system, "\n\n".join(parts)


async def generate_json(
    *,
    task: str,
    schema: type[T],
    instructions: str,
    trusted: str,
    untrusted: Sequence[Untrusted] = (),
    tier: Tier,
    offer: OfferLLMContext,
    deps: LLMDeps,
    max_tokens: int = 4000,
    effort: Effort | None = None,
    now: datetime | None = None,
) -> Generated[T]:
    """Ask a model for JSON matching `schema`, with every guard in front of the call.

    Raises BudgetExceeded, UntrustedInputRejected, LLMRefused, LLMOutputInvalid, or the
    registry's NothingConfigured / AllProvidersFailed. Callers skip the item on any of them.
    """
    now = now or datetime.now(UTC)

    if await deps.meter.is_paused(offer.offer_id):
        raise BudgetExceeded("paused", "LLM work is paused for this offer until a human resumes it")

    for item in untrusted:
        result = screen(item.text)
        if result.flagged:
            raise UntrustedInputRejected(item.source, result.reasons)

    system, user = build_prompt(instructions, trusted, untrusted)
    request = LLMRequest(
        tier=tier,
        system=system,
        user=user,
        max_tokens=max_tokens,
        effort=effort or DEFAULT_EFFORT[tier],
    )

    async def call(provider: LLMProvider) -> Generated[T]:
        model = provider.model_for(tier)
        estimate = estimate_usd(model, len(system) + len(user), max_tokens)
        spend = await deps.meter.spend(offer.offer_id, now)
        decision = decide(offer.budget, spend, estimate, now.date())
        if decision == "monthly_limit":
            reason = (
                f"monthly LLM budget ${offer.budget.monthly_usd} reached "
                f"(spent ${spend.month_usd}, next call up to ${estimate})"
            )
            await deps.meter.pause(offer.offer_id, reason)
            raise BudgetExceeded(decision, reason)
        if decision == "daily_limit":
            raise BudgetExceeded(
                decision, f"today's LLM budget is used up (spent ${spend.day_usd})"
            )

        for attempt in (1, 2):
            completion = await provider.complete_json(request, schema)
            usd = await _record(deps, offer, task, completion)
            if completion.refused:
                raise LLMRefused(f"{completion.model} declined task {task}")
            if completion.parsed is not None and isinstance(completion.parsed, schema):
                return Generated(completion.parsed, completion.provider, completion.model, usd)
            log.warning("task %s attempt %d: output did not match schema", task, attempt)
        raise LLMOutputInvalid(f"{provider.name} returned invalid output twice for task {task}")

    served = await deps.providers.first(offer.provider_order, call)
    return served.value


async def _record(
    deps: LLMDeps, offer: OfferLLMContext, task: str, completion: Completion
) -> Decimal:
    usd = cost_usd(completion.model, completion.usage)
    await deps.meter.record(
        offer_id=offer.offer_id,
        run_id=deps.run_id,
        provider=completion.provider,
        model=completion.model,
        task=task,
        usage=completion.usage,
        usd=usd,
    )
    return usd
