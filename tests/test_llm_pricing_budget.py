from datetime import date
from decimal import Decimal

import pytest

from si.llm.budget import Budget, Spend, decide
from si.llm.pricing import PriceUnknown, cost_usd, estimate_usd
from si.llm.types import Usage


def test_opus_cost() -> None:
    usage = Usage(input_tokens=15_000, output_tokens=2_000, cache_read_tokens=10_000)
    # 15k * $4 + 2k * $20 + 10k * $0.20, per million
    assert cost_usd("claude-opus-5-5", usage) == Decimal("0.102000")


def test_haiku_long_context_tier() -> None:
    short = cost_usd("claude-haiku-5-5", Usage(input_tokens=100_000, output_tokens=1_000))
    long = cost_usd("claude-haiku-5-5", Usage(input_tokens=100_001, output_tokens=1_000))
    assert short == Decimal("0.010500")
    assert long == Decimal("0.052501")


def test_unknown_model_is_refused() -> None:
    with pytest.raises(PriceUnknown):
        cost_usd("some-new-model", Usage())


def test_estimate_assumes_all_output_used() -> None:
    assert estimate_usd("claude-opus-5-5", 3_000, 1_000) == cost_usd(
        "claude-opus-5-5", Usage(input_tokens=1_001, output_tokens=1_000)
    )


OCT = date(2026, 10, 22)  # 31 days


@pytest.mark.parametrize(
    ("month", "day", "estimate", "expected"),
    [
        ("0", "0", "0.10", "ok"),
        ("10", "1.55", "0.10", "daily_limit"),  # 50/31 = 1.612903
        ("49.95", "0", "0.10", "monthly_limit"),
        ("50", "0", "0", "ok"),
    ],
)
def test_budget_decision(month: str, day: str, estimate: str, expected: str) -> None:
    budget = Budget(monthly_usd=Decimal(50))
    spend = Spend(month_usd=Decimal(month), day_usd=Decimal(day))
    assert decide(budget, spend, Decimal(estimate), OCT) == expected


def test_explicit_daily_budget_wins() -> None:
    budget = Budget(monthly_usd=Decimal(50), daily_usd=Decimal("0.05"))
    assert decide(budget, Spend(Decimal(0), Decimal(0)), Decimal("0.06"), OCT) == "daily_limit"
