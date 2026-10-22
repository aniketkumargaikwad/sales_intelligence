from pathlib import Path
from typing import Any

import pytest

from si.db import migrate as migrations

pytestmark = pytest.mark.db


async def test_all_applied_and_rerun_is_noop(db: Any) -> None:
    state = await migrations.status(db)
    assert state.pending == []
    assert state.applied == [m.version for m in migrations.discover()]
    assert await migrations.migrate(db) == []


async def test_changed_migration_is_detected(db: Any, tmp_path: Path) -> None:
    for m in migrations.discover():
        (tmp_path / m.path.name).write_text(m.sql)
    first = sorted(tmp_path.glob("*.sql"))[0]
    first.write_text(first.read_text() + "\n-- edited\n")
    with pytest.raises(migrations.MigrationError, match="changed after it was applied"):
        await migrations.status(db, tmp_path)


def test_bad_filename_rejected(tmp_path: Path) -> None:
    (tmp_path / "1_x.sql").write_text("select 1")
    with pytest.raises(migrations.MigrationError, match=r"NNNN_name\.sql"):
        migrations.discover(tmp_path)
