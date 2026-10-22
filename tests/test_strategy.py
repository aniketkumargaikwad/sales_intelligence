import shutil
from pathlib import Path

import pytest

from si import strategy
from si.cli import main
from si.config.offer import load_offer, readiness_gaps
from tests.conftest import EXAMPLE_OFFER, ROOT

UK_OFFER = ROOT / "offers" / "uk-webdesign-test"


@pytest.fixture
def pack(tmp_path: Path) -> Path:
    """A writable copy of the UK test offer and its strategy pack."""
    folder = tmp_path / "offers" / "uk-webdesign-test"
    shutil.copytree(UK_OFFER, folder)
    return folder


def errors(folder: Path) -> list[strategy.Finding]:
    return [f for f in strategy.check_pack(load_offer(folder)) if f.level == "error"]


def append(folder: Path, filename: str, text: str) -> None:
    path = folder / "strategy" / filename
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def test_committed_uk_pack_is_clean() -> None:
    assert strategy.check_pack(load_offer(UK_OFFER)) == []


def test_offer_without_a_pack_lists_every_missing_doc() -> None:
    findings = strategy.check_pack(load_offer(EXAMPLE_OFFER))
    assert {f.file for f in findings} == {spec.filename for spec in strategy.PACK}
    assert all(f.message == "missing" for f in findings)


def test_missing_section(pack: Path) -> None:
    path = pack / "strategy" / "01-icp.md"
    path.write_text(path.read_text().replace("## Disqualifiers", "## Not for us"))
    assert [f.message for f in errors(pack)] == ["missing section '## Disqualifiers'"]


def test_front_matter_must_match_the_offer(pack: Path) -> None:
    path = pack / "strategy" / "02-personas.md"
    path.write_text(path.read_text().replace("doc: personas", "doc: icp"))
    assert [f.message for f in errors(pack)] == ["front matter doc must be 'personas'"]


def test_doc_without_front_matter(pack: Path) -> None:
    path = pack / "strategy" / "07-funnel.md"
    path.write_text(path.read_text().split("---\n", 2)[2])
    assert [f.message for f in errors(pack)] == ["missing front matter (--- ... ---)"]


def test_changed_offer_yaml_warns_that_the_pack_is_stale(pack: Path) -> None:
    offer_yaml = pack / "offer.yaml"
    offer_yaml.write_text(offer_yaml.read_text() + "\n# edited\n")
    findings = strategy.check_pack(load_offer(pack))
    assert findings and all(f.level == "warning" for f in findings)
    assert len(findings) == len(strategy.PACK)


def test_invented_price_is_an_error(pack: Path) -> None:
    append(pack, "04-messaging-house.md", "\nIntro offer: £499 for the first page.\n")
    found = errors(pack)
    assert len(found) == 1 and "'£499' is not one of our prices" in found[0].message
    assert found[0].line > 0


def test_offer_price_and_our_budget_are_allowed(pack: Path) -> None:
    append(pack, "04-messaging-house.md", "\nIt is £1,800 per site; we spend $30 a month.\n")
    assert errors(pack) == []


def test_prospect_numbers_need_a_source_mark(pack: Path) -> None:
    append(pack, "01-icp.md", "\nThey spend £5k a year on ads.\n40% have no booking page.\n")
    assert len(errors(pack)) == 2
    append(pack, "07-funnel.md", "\nThey spend £5k a year on ads (estimate).\n")
    append(pack, "07-funnel.md", "40% reply (source: https://example.org/survey).\n")
    assert len(errors(pack)) == 2  # only the two unmarked lines in 01-icp.md


def test_customer_claims_need_proof(pack: Path) -> None:
    append(pack, "03-positioning.md", "\nTrusted by dozens of local trades.\n")
    assert ["offer.proof is empty" in f.message for f in errors(pack)] == [True]


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("> Get a free audit today.", "banned word 'free'"),
        ("> Results guaranteed.", "banned word 'guaranteed'"),
        ("> Re: your website", "fakes a reply"),
    ],
)
def test_sample_copy_follows_outbound_rules(pack: Path, line: str, message: str) -> None:
    append(pack, "04-messaging-house.md", f"\n{line}\n")
    found = errors(pack)
    assert len(found) == 1 and message in found[0].message


def test_hype_words_outside_sample_copy_are_allowed(pack: Path) -> None:
    append(pack, "04-messaging-house.md", "\nWe never say free or guaranteed.\n")
    assert errors(pack) == []


def test_cli_strategy_check(pack: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["strategy", "check", str(pack)]) == 0
    assert "complete and clean" in capsys.readouterr().out
    append(pack, "05-objections.md", "\nWe can do it for £999.\n")
    assert main(["strategy", "check", str(pack)]) == 1
    assert "1 error(s)" in capsys.readouterr().out


def test_cli_strategy_hash(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["strategy", "hash", str(UK_OFFER)]) == 0
    assert capsys.readouterr().out.strip() == strategy.offer_hash(load_offer(UK_OFFER))


def test_readiness_gaps() -> None:
    assert readiness_gaps(load_offer(UK_OFFER).config) == []
    gaps = readiness_gaps(load_offer(ROOT / "offers" / "voicesync").config)
    assert any("postal_address" in g for g in gaps)
    assert any("test_mode_only_to" in g for g in gaps)
