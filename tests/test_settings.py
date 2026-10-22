import pytest

from si.config.settings import Settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "test"),
        ("", "test"),
        ("test", "test"),
        ("LIVE", "live"),
        (" live ", "live"),
        ("yes", "test"),
        ("production", "test"),
    ],
)
def test_send_mode_fails_closed(
    monkeypatch: pytest.MonkeyPatch, raw: str | None, expected: str
) -> None:
    if raw is not None:
        monkeypatch.setenv("SI_SEND_MODE", raw)
    settings = Settings()
    assert settings.send_mode == expected
    assert settings.test_mode is (expected == "test")


def test_only_to_accepts_legacy_name_and_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONLY_TO", "Founder@Example.com, ops@example.com,")
    assert Settings().only_to == ["founder@example.com", "ops@example.com"]


def test_database_url_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    settings = Settings()
    assert settings.database_url is not None
    assert settings.database_url.get_secret_value() == "postgresql://x"
    assert "postgresql://x" not in repr(settings)
