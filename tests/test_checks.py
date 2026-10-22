from pathlib import Path

import pytest

from si.checks.base import CheckResult
from si.checks.dns import check_domain
from si.checks.run import exit_code, render, run_checks
from si.config.settings import Settings
from tests.conftest import EXAMPLE_OFFER
from tests.fakes import ScriptedLLM

RECORDS = {
    "example.com": ["v=spf1 include:zoho.in ~all", "google-site-verification=x"],
    "_dmarc.example.com": ["v=DMARC1; p=quarantine; rua=mailto:d@example.com"],
    "zoho._domainkey.example.com": ["v=DKIM1; k=rsa; p=MIGf"],
}


def test_dns_all_present() -> None:
    results = check_domain("example.com", ["default", "zoho"], lambda n: RECORDS.get(n, []))
    assert [r.status for r in results] == ["ok", "ok", "ok"]
    assert "quarantine" in results[1].detail and "zoho" in results[2].detail


def test_dns_all_missing() -> None:
    results = check_domain("bare.test", ["default"], lambda n: [])
    assert [r.status for r in results] == ["failing"] * 3


def test_dns_duplicate_spf() -> None:
    results = check_domain(
        "x.test", [], lambda n: ["v=spf1 a", "v=spf1 mx"] if n == "x.test" else []
    )
    assert "more than one" in results[0].detail


async def fake_dns(domains, selectors):  # type: ignore[no-untyped-def]
    return [CheckResult.ok(f"dns: {d}") for d in domains]


async def test_run_checks_without_database_fails(tmp_path: Path) -> None:
    offers = tmp_path / "offers"
    (offers / "acme").mkdir(parents=True)
    (offers / "acme" / "offer.yaml").write_text((EXAMPLE_OFFER / "offer.yaml").read_text())
    settings = Settings(offers_dir=offers)
    results = await run_checks(
        settings, llm_providers=[ScriptedLLM("anthropic", [])], dns_check=fake_dns
    )
    by = {r.component: r for r in results}
    assert by["config: acme"].status == "ok"
    assert "sam.personal@example.com" in by["send mode"].detail
    assert by["database"].status == "failing"
    assert by["llm: anthropic"].status == "ok"
    assert by["mailbox: smtp login"].status == "not_configured"
    assert by["dns: example.com"].status == "ok"
    assert exit_code(results) == 1
    assert "1 failing" in render(results)


async def test_only_groups(tmp_path: Path) -> None:
    results = await run_checks(Settings(offers_dir=tmp_path), llm_providers=[], only={"send_mode"})
    assert [r.component for r in results] == ["send mode"]
    assert exit_code(results) == 0


@pytest.mark.db
async def test_database_check_ok(database_url: str, tmp_path: Path) -> None:
    results = await run_checks(
        Settings(offers_dir=tmp_path, database_url=database_url),
        llm_providers=[],
        only={"database"},
    )
    assert results[0].status == "ok", results[0].detail
