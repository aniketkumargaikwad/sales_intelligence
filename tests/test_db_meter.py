from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from si.llm.budget import PostgresMeter
from si.llm.types import Usage

pytestmark = pytest.mark.db


async def test_spend_month_and_day(db: Any, offer_id: UUID) -> None:
    meter = PostgresMeter(db)
    now = datetime(2026, 10, 22, 12, tzinfo=UTC)
    for at, usd in [
        (now, "0.50"),
        (now - timedelta(days=2), "1.25"),
        (now - timedelta(days=40), "9"),
    ]:
        await db.execute(
            "insert into costs (offer_id, provider, usd, at) values ($1, 'anthropic', $2, $3)",
            offer_id,
            Decimal(usd),
            at,
        )
    spend = await meter.spend(offer_id, now)
    assert spend.month_usd == Decimal("1.75")
    assert spend.day_usd == Decimal("0.50")


async def test_record_and_pause(db: Any, offer_id: UUID) -> None:
    meter = PostgresMeter(db)
    await meter.record(
        offer_id=offer_id,
        run_id=None,
        provider="anthropic",
        model="claude-haiku-5-5",
        task="t",
        usage=Usage(input_tokens=10),
        usd=Decimal("0.000001"),
    )
    assert await db.fetchval("select count(*) from costs where offer_id = $1", offer_id) == 1
    assert not await meter.is_paused(offer_id)
    await meter.pause(offer_id, "budget")
    await meter.pause(offer_id, "budget again")
    assert await meter.is_paused(offer_id)
    assert (
        await db.fetchval(
            "select count(*) from audit_log where offer_id = $1 and action = 'llm_paused'", offer_id
        )
        == 2
    )
