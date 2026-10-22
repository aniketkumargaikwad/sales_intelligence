"""Spend tracking and the LLM budget gate (design §5.7, brief §6 "spend gate").

- Over the day's budget: skip LLM work for the rest of the UTC day.
- Over the month's budget: set `llm_paused` for the offer. Only a human clears it.
"""

from __future__ import annotations

import calendar
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal, Protocol
from uuid import UUID

from si.llm.types import Usage

PAUSE_KEY = "llm_paused"

Decision = Literal["ok", "daily_limit", "monthly_limit"]


@dataclass(frozen=True)
class Budget:
    monthly_usd: Decimal
    daily_usd: Decimal | None = None

    def daily_limit(self, today: date) -> Decimal:
        if self.daily_usd is not None:
            return self.daily_usd
        days = calendar.monthrange(today.year, today.month)[1]
        return (self.monthly_usd / days).quantize(Decimal("0.000001"))


@dataclass(frozen=True)
class Spend:
    month_usd: Decimal
    day_usd: Decimal


def decide(budget: Budget, spend: Spend, estimate: Decimal, today: date) -> Decision:
    if spend.month_usd + estimate > budget.monthly_usd:
        return "monthly_limit"
    if spend.day_usd + estimate > budget.daily_limit(today):
        return "daily_limit"
    return "ok"


class Meter(Protocol):
    async def spend(self, offer_id: UUID, now: datetime) -> Spend: ...

    async def is_paused(self, offer_id: UUID) -> bool: ...

    async def pause(self, offer_id: UUID, reason: str) -> None: ...

    async def record(
        self,
        *,
        offer_id: UUID,
        run_id: UUID | None,
        provider: str,
        model: str,
        task: str,
        usage: Usage,
        usd: Decimal,
    ) -> None: ...


class PostgresMeter:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    async def spend(self, offer_id: UUID, now: datetime) -> Spend:
        now = now.astimezone(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        row = await self.conn.fetchrow(
            """
            select coalesce(sum(usd), 0) as month_usd,
                   coalesce(sum(usd) filter (where at >= $3), 0) as day_usd
            from costs where offer_id = $1 and at >= $2
            """,
            offer_id,
            month_start,
            day_start,
        )
        return Spend(month_usd=Decimal(row["month_usd"]), day_usd=Decimal(row["day_usd"]))

    async def is_paused(self, offer_id: UUID) -> bool:
        value = await self.conn.fetchval(
            "select value from settings where key = $1 and (offer_id = $2 or offer_id is null)"
            " and value = 'true'::jsonb limit 1",
            PAUSE_KEY,
            offer_id,
        )
        return value is not None

    async def pause(self, offer_id: UUID, reason: str) -> None:
        async with self.conn.transaction():
            await self.conn.execute(
                """
                insert into settings (offer_id, key, value, set_by, reason)
                values ($1, $2, 'true'::jsonb, 'engine', $3)
                on conflict (coalesce(offer_id, '00000000-0000-0000-0000-000000000000'::uuid), key)
                do update set value = excluded.value, set_by = excluded.set_by,
                              reason = excluded.reason, set_at = now()
                """,
                offer_id,
                PAUSE_KEY,
                reason,
            )
            await self.conn.execute(
                "insert into audit_log (offer_id, actor, action, detail)"
                " values ($1, 'engine', 'llm_paused', $2::jsonb)",
                offer_id,
                json.dumps({"reason": reason}),
            )

    async def record(
        self,
        *,
        offer_id: UUID,
        run_id: UUID | None,
        provider: str,
        model: str,
        task: str,
        usage: Usage,
        usd: Decimal,
    ) -> None:
        await self.conn.execute(
            "insert into costs (offer_id, run_id, provider, model, task, units, usd)"
            " values ($1, $2, $3, $4, $5, $6::jsonb, $7)",
            offer_id,
            run_id,
            provider,
            model,
            task,
            json.dumps(usage.as_dict()),
            usd,
        )
