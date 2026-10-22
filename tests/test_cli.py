from pathlib import Path

import pytest

from si.cli import main
from tests.conftest import EXAMPLE_OFFER


def test_validate_example(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(EXAMPLE_OFFER)]) == 0
    assert "ok   example" in capsys.readouterr().out


def test_validate_bad(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / "broken"
    folder.mkdir()
    (folder / "offer.yaml").write_text("offer: {}\n")
    assert main(["validate", str(folder)]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_keepalive_skips_cleanly_without_database(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", "--only", "database", "--skip-if-unconfigured"]) == 0
    assert "skipping check" in capsys.readouterr().out


def test_migrate_without_database(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["migrate"]) == 1
    assert "SI_DATABASE_URL" in capsys.readouterr().out
