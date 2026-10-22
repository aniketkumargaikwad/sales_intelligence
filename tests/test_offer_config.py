from pathlib import Path

import pytest
import yaml

from si.config.offer import OfferConfigError, load_offer, offer_dirs
from tests.conftest import EXAMPLE_OFFER


def write_offer(tmp_path: Path, mutate=None, slug: str = "acme") -> Path:  # type: ignore[no-untyped-def]
    data = yaml.safe_load((EXAMPLE_OFFER / "offer.yaml").read_text())
    if mutate:
        mutate(data)
    folder = tmp_path / "offers" / slug
    folder.mkdir(parents=True)
    (folder / "offer.yaml").write_text(yaml.safe_dump(data))
    return folder


def test_example_offer_is_valid() -> None:
    offer = load_offer(EXAMPLE_OFFER)
    assert offer.slug == "example"
    assert offer.config.offer.price.from_ == "£1,200 one-off"
    assert offer.config.constraints.approval == "required"


def test_cold_channels_can_never_be_allowed(tmp_path: Path) -> None:
    folder = write_offer(
        tmp_path, lambda d: d["channels"].update(allowed=["email", "cold_call"], forbidden=[])
    )
    with pytest.raises(OfferConfigError, match="can never be allowed: cold_call"):
        load_offer(folder)


def test_approval_cannot_be_turned_off(tmp_path: Path) -> None:
    folder = write_offer(tmp_path, lambda d: d["constraints"].update(approval="optional"))
    with pytest.raises(OfferConfigError, match=r"constraints\.approval"):
        load_offer(folder)


def test_typos_are_rejected(tmp_path: Path) -> None:
    folder = write_offer(tmp_path, lambda d: d["offer"].update(pricee="oops"))
    with pytest.raises(OfferConfigError, match=r"offer\.pricee"):
        load_offer(folder)


def test_bad_timezone_and_country(tmp_path: Path) -> None:
    folder = write_offer(
        tmp_path,
        lambda d: d["market"].update(geographies=[{"country": "uk", "timezone": "Mars/Base"}]),
    )
    with pytest.raises(OfferConfigError) as exc:
        load_offer(folder)
    assert "ISO 3166-1" in str(exc.value)
    assert "unknown timezone" in str(exc.value)


def test_bad_email_in_allow_list(tmp_path: Path) -> None:
    folder = write_offer(
        tmp_path, lambda d: d["constraints"].update(test_mode_only_to=["not-an-email"])
    )
    with pytest.raises(OfferConfigError, match="not an email address"):
        load_offer(folder)


def test_scraper_needs_opt_in(tmp_path: Path) -> None:
    folder = write_offer(tmp_path, lambda d: d.update(providers={"discovery": ["gmaps_scraper"]}))
    with pytest.raises(OfferConfigError, match="allow_scraper"):
        load_offer(folder)


def test_offer_dirs_skip_examples(tmp_path: Path) -> None:
    write_offer(tmp_path, slug="acme")
    write_offer(tmp_path, slug="_draft")
    assert [p.name for p in offer_dirs(tmp_path / "offers")] == ["acme"]
