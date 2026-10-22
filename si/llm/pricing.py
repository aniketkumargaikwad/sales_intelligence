from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from si.llm.types import Usage

PRICES_FILE = Path(__file__).with_name("prices.yaml")
MILLION = Decimal(1_000_000)


class PriceUnknown(Exception):
    """We refuse to call a model we can't price: the budget gate would be blind."""


@dataclass(frozen=True)
class Rates:
    input: Decimal
    output: Decimal
    cache_read: Decimal
    cache_write: Decimal


@dataclass(frozen=True)
class ModelPrice:
    base: Rates
    long_context_above: int | None = None
    long_context: Rates | None = None

    def rates_for(self, total_input_tokens: int) -> Rates:
        if (
            self.long_context is not None
            and self.long_context_above is not None
            and total_input_tokens > self.long_context_above
        ):
            return self.long_context
        return self.base


def _rates(raw: dict[str, Any]) -> Rates:
    return Rates(
        input=Decimal(str(raw["input"])),
        output=Decimal(str(raw["output"])),
        cache_read=Decimal(str(raw.get("cache_read", raw["input"]))),
        cache_write=Decimal(str(raw.get("cache_write", raw["input"]))),
    )


@cache
def price_table(path: Path = PRICES_FILE) -> dict[str, ModelPrice]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    table: dict[str, ModelPrice] = {}
    for model, spec in raw["models"].items():
        long = spec.get("long_context")
        table[model] = ModelPrice(
            base=_rates(spec),
            long_context_above=long["above_input_tokens"] if long else None,
            long_context=_rates(long) if long else None,
        )
    return table


def model_price(model: str) -> ModelPrice:
    try:
        return price_table()[model]
    except KeyError:
        raise PriceUnknown(f"no price for model {model!r} in si/llm/prices.yaml") from None


def cost_usd(model: str, usage: Usage) -> Decimal:
    total_input = usage.input_tokens + usage.cache_read_tokens + usage.cache_write_tokens
    r = model_price(model).rates_for(total_input)
    usd = (
        Decimal(usage.input_tokens) * r.input
        + Decimal(usage.output_tokens) * r.output
        + Decimal(usage.cache_read_tokens) * r.cache_read
        + Decimal(usage.cache_write_tokens) * r.cache_write
    ) / MILLION
    return usd.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def estimate_usd(model: str, prompt_chars: int, max_tokens: int) -> Decimal:
    """Worst-case cost before a call: ~3 characters per token, every output token used."""
    return cost_usd(model, Usage(input_tokens=prompt_chars // 3 + 1, output_tokens=max_tokens))
