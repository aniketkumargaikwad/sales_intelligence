"""Plain-SQL migrations (ADR-0002): `db/migrations/NNNN_name.sql`, applied in order, once.

Each file runs in its own transaction. An applied file whose contents later change is an error:
fix forward with a new migration instead of editing history.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"
FILENAME_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
LOCK_KEY = 0x5A1E5  # advisory lock id: one migrator at a time

BOOTSTRAP = """
create table if not exists schema_migrations (
  version    text primary key,
  name       text not null,
  checksum   text not null,
  applied_at timestamptz not null default now()
)
"""


class MigrationError(Exception):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    path: Path

    @property
    def sql(self) -> str:
        return self.path.read_text(encoding="utf-8")

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


def discover(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    found: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        match = FILENAME_RE.match(path.name)
        if not match:
            raise MigrationError(f"{path.name}: migration files must be named NNNN_name.sql")
        found.append(Migration(version=match.group(1), name=match.group(2), path=path))
    versions = [m.version for m in found]
    if len(versions) != len(set(versions)):
        raise MigrationError("two migration files share a version number")
    return found


@dataclass(frozen=True)
class MigrationStatus:
    applied: list[str]
    pending: list[Migration]


async def status(conn: Any, directory: Path = MIGRATIONS_DIR) -> MigrationStatus:
    migrations = discover(directory)
    exists = await conn.fetchval("select to_regclass('public.schema_migrations') is not null")
    applied: dict[str, str] = {}
    if exists:
        rows = await conn.fetch("select version, checksum from schema_migrations")
        applied = {r["version"]: r["checksum"] for r in rows}
    for m in migrations:
        if m.version in applied and applied[m.version] != m.checksum:
            raise MigrationError(
                f"migration {m.path.name} was changed after it was applied; "
                "add a new migration instead"
            )
    return MigrationStatus(
        applied=sorted(applied),
        pending=[m for m in migrations if m.version not in applied],
    )


async def migrate(conn: Any, directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    """Apply pending migrations. Returns the ones applied in this call."""
    await conn.execute("select pg_advisory_lock($1)", LOCK_KEY)
    try:
        await conn.execute(BOOTSTRAP)
        pending = (await status(conn, directory)).pending
        for m in pending:
            async with conn.transaction():
                await conn.execute(m.sql)
                await conn.execute(
                    "insert into schema_migrations (version, name, checksum) values ($1, $2, $3)",
                    m.version,
                    m.name,
                    m.checksum,
                )
        return pending
    finally:
        await conn.execute("select pg_advisory_unlock($1)", LOCK_KEY)
