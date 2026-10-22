"""Browser sessions (authenticated role) only see offers they belong to."""

import json
from typing import Any
from uuid import UUID, uuid4

import asyncpg
import pytest

pytestmark = pytest.mark.db


async def as_user(db: Any, user: UUID, sql: str, *args: Any) -> list[Any]:
    async with db.transaction():
        await db.execute("set local role authenticated")
        await db.execute(
            "select set_config('request.jwt.claims', $1, true)", json.dumps({"sub": str(user)})
        )
        rows: list[Any] = await db.fetch(sql, *args)
        return rows


async def two_offers(db: Any) -> tuple[UUID, UUID, UUID]:
    a = await db.fetchval(
        "insert into offers (slug, name) values ($1, 'A') returning id", f"a-{uuid4().hex[:8]}"
    )
    b = await db.fetchval(
        "insert into offers (slug, name) values ($1, 'B') returning id", f"b-{uuid4().hex[:8]}"
    )
    user = uuid4()
    await db.execute(
        "insert into offer_members (offer_id, user_id, role) values ($1, $2, 'approver')", a, user
    )
    for offer in (a, b):
        await db.execute(
            "insert into messages (offer_id, channel, status, subject)"
            " values ($1, 'email', 'draft', 's')",
            offer,
        )
    return a, b, user


async def test_members_see_only_their_offers(db: Any) -> None:
    a, b, user = await two_offers(db)
    offers = {r["id"] for r in await as_user(db, user, "select id from offers")}
    assert a in offers and b not in offers
    msgs = {r["offer_id"] for r in await as_user(db, user, "select offer_id from messages")}
    assert msgs == {a}


async def test_strangers_see_nothing(db: Any) -> None:
    await two_offers(db)
    assert await as_user(db, uuid4(), "select id from messages") == []


async def test_approver_cannot_touch_other_offer(db: Any) -> None:
    a, b, user = await two_offers(db)
    updated = await as_user(
        db, user, "update messages set status = 'rejected' where offer_id = $1 returning id", b
    )
    assert updated == []
    updated = await as_user(
        db, user, "update messages set status = 'rejected' where offer_id = $1 returning id", a
    )
    assert len(updated) == 1


async def test_members_cannot_delete_suppression_or_write_costs(db: Any) -> None:
    a, _, user = await two_offers(db)
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await as_user(db, user, "delete from suppression")
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await as_user(
            db, user, "insert into costs (offer_id, provider, usd) values ($1, 'x', 0)", a
        )


async def test_anon_has_no_access(db: Any) -> None:
    async with db.transaction():
        await db.execute("set local role anon")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await db.fetch("select * from messages")
