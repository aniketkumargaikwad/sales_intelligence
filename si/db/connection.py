from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from si.config.settings import Settings


class DatabaseNotConfigured(Exception):
    pass


def database_url(settings: Settings) -> str:
    if settings.database_url is None:
        raise DatabaseNotConfigured("SI_DATABASE_URL is not set")
    return settings.database_url.get_secret_value()


@asynccontextmanager
async def connect(settings: Settings, *, timeout: float = 15) -> AsyncIterator[Any]:
    # statement_cache_size=0 keeps us compatible with Supabase's transaction pooler.
    conn = await asyncpg.connect(database_url(settings), timeout=timeout, statement_cache_size=0)
    try:
        yield conn
    finally:
        await conn.close()
