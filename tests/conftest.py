from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

from si.db import migrate as migrations

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_OFFER = ROOT / "offers" / "_example"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Tests never read the developer's real .env or credentials."""
    for key in list(os.environ):
        if key.startswith("SI_") or key in {
            "DATABASE_URL",
            "ONLY_TO",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
        }:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


def _with_db(url: str, name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{name}"))


@pytest.fixture(scope="session")
async def database_url() -> AsyncIterator[str]:
    base = os.environ.get("SI_TEST_DATABASE_URL")
    if not base:
        pytest.skip("SI_TEST_DATABASE_URL is not set")
    name = f"si_test_{uuid.uuid4().hex[:10]}"
    admin = await asyncpg.connect(base)
    await admin.execute(f'create database "{name}"')
    url = _with_db(base, name)
    conn = await asyncpg.connect(url)
    await migrations.migrate(conn)
    await conn.close()
    try:
        yield url
    finally:
        await admin.execute(f'drop database "{name}" with (force)')
        await admin.close()


@pytest.fixture
async def db(database_url: str) -> AsyncIterator[Any]:
    conn = await asyncpg.connect(database_url)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def offer_id(db: Any) -> uuid.UUID:
    slug = f"t-{uuid.uuid4().hex[:12]}"
    value: uuid.UUID = await db.fetchval(
        "insert into offers (slug, name) values ($1, $2) returning id", slug, "Test offer"
    )
    return value
