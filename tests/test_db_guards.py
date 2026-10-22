"""The database itself refuses unsafe states (design §5.9, §5.10)."""

from typing import Any
from uuid import UUID

import asyncpg
import pytest

pytestmark = pytest.mark.db


async def new_message(db: Any, offer_id: UUID, status: str = "draft") -> UUID:
    value: UUID = await db.fetchval(
        "insert into messages (offer_id, channel, status, to_address, subject, body)"
        " values ($1, 'email', $2, 'a@b.test', 'Hello', 'Body') returning id",
        offer_id,
        status,
    )
    return value


async def set_status(db: Any, message_id: UUID, status: str, **extra: Any) -> None:
    sets = ", ".join(f"{k} = ${i + 3}" for i, k in enumerate(extra))
    sql = f"update messages set status = $2{', ' + sets if sets else ''} where id = $1"
    await db.execute(sql, message_id, status, *extra.values())


async def test_cannot_insert_as_approved(db: Any, offer_id: UUID) -> None:
    with pytest.raises(asyncpg.RaiseError, match="must start as"):
        await new_message(db, offer_id, "approved")


async def test_approval_needs_who_and_when(db: Any, offer_id: UUID) -> None:
    mid = await new_message(db, offer_id)
    with pytest.raises(asyncpg.RaiseError, match="needs approved_by"):
        await set_status(db, mid, "approved")
    await db.execute(
        "update messages set status = 'approved', approved_by = 'founder', approved_at = now()"
        " where id = $1",
        mid,
    )
    assert await db.fetchval("select status from messages where id = $1", mid) == "approved"


async def test_cannot_skip_approval_to_sent(db: Any, offer_id: UUID) -> None:
    mid = await new_message(db, offer_id)
    with pytest.raises(asyncpg.RaiseError, match="cannot move from draft to sent"):
        await set_status(db, mid, "sent")
    with pytest.raises(asyncpg.RaiseError, match="cannot move from draft to sending"):
        await set_status(db, mid, "sending")


async def approved(db: Any, offer_id: UUID) -> UUID:
    mid = await new_message(db, offer_id)
    await db.execute(
        "update messages set status = 'approved', approved_by = 'founder', approved_at = now()"
        " where id = $1",
        mid,
    )
    return mid


async def test_happy_path_sets_sent_at(db: Any, offer_id: UUID) -> None:
    mid = await approved(db, offer_id)
    await set_status(db, mid, "sending")
    await set_status(db, mid, "sent")
    row = await db.fetchrow("select status, sent_at from messages where id = $1", mid)
    assert row["status"] == "sent" and row["sent_at"] is not None


async def test_approved_content_is_frozen(db: Any, offer_id: UUID) -> None:
    mid = await approved(db, offer_id)
    with pytest.raises(asyncpg.RaiseError, match="move it back to draft"):
        await db.execute("update messages set body = 'changed' where id = $1", mid)
    with pytest.raises(asyncpg.RaiseError, match="move it back to draft"):
        await db.execute("update messages set to_address = 'x@y.test' where id = $1", mid)


async def test_back_to_draft_drops_approval(db: Any, offer_id: UUID) -> None:
    mid = await approved(db, offer_id)
    await db.execute("update messages set status = 'draft', body = 'edited' where id = $1", mid)
    row = await db.fetchrow("select approved_by, approved_at from messages where id = $1", mid)
    assert row["approved_by"] is None and row["approved_at"] is None


async def test_held_needs_approval_to_release(db: Any, offer_id: UUID) -> None:
    mid = await approved(db, offer_id)
    await set_status(db, mid, "held")
    await set_status(db, mid, "approved")
    await set_status(db, mid, "sending")


async def test_suppression_is_append_only(db: Any, offer_id: UUID) -> None:
    sid = await db.fetchval(
        "insert into suppression (offer_id, value, kind, reason, source, created_by)"
        " values ($1, '  Someone@Example.COM ', 'email', 'unsubscribed', 'test', 'test')"
        " returning id",
        offer_id,
    )
    assert (
        await db.fetchval("select value from suppression where id = $1", sid)
        == "someone@example.com"
    )
    with pytest.raises(asyncpg.RaiseError, match="append-only"):
        await db.execute("update suppression set value = 'x' where id = $1", sid)
    with pytest.raises(asyncpg.RaiseError, match="append-only"):
        await db.execute("delete from suppression where id = $1", sid)
    with pytest.raises(asyncpg.RaiseError, match="append-only"):
        await db.execute("truncate suppression")


async def test_domain_suppression_strips_at(db: Any, offer_id: UUID) -> None:
    value = await db.fetchval(
        "insert into suppression (offer_id, value, kind, reason, source, created_by)"
        " values ($1, '@Example.org', 'domain', 'asked', 'test', 'test') returning value",
        offer_id,
    )
    assert value == "example.org"


async def test_facts_need_a_source(db: Any, offer_id: UUID) -> None:
    with pytest.raises(asyncpg.CheckViolationError):
        await db.execute(
            "insert into facts (offer_id, entity_type, entity_id, key, value, source_url,"
            " source_kind) values ($1, 'account', gen_random_uuid(), 'hours', '\"9-5\"',"
            " 'somewhere', 'website')",
            offer_id,
        )
