"""The Offer Brief: `offers/<slug>/offer.yaml` (brief §2), validated strictly.

Everything specific to an offer lives here, so a typo must fail loudly rather than silently
fall back to a default.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Brief §1.12 and §7: never, for any offer, in any country.
NEVER_ALLOWED_CHANNELS = frozenset({"cold_call", "cold_sms", "cold_whatsapp"})

Channel = Literal[
    "email",
    "linkedin_manual",
    "whatsapp_manual",
    "instagram_manual",
    "visit",
    "call_inbound",
    "cold_call",
    "cold_sms",
    "cold_whatsapp",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _check_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_RE.match(value):
        raise ValueError(f"not an email address: {value!r}")
    return value


class Price(Strict):
    from_: str = Field(alias="from")
    upfront: str | None = None
    trial: str | None = None


class Proof(Strict):
    customers: list[str] = []
    case_studies: list[str] = []
    numbers: list[str] = []


class Objection(Strict):
    objection: str
    answer: str


class ProofAssetConfig(Strict):
    adapter: str = "none"
    description: str = ""
    url: str | None = None


class OfferSection(Strict):
    name: str
    one_liner: str
    type: Literal["saas", "service", "product", "agency", "marketplace"]
    website: str | None = None
    price: Price
    proof: Proof = Proof()
    differentiators: list[str] = []
    objections: list[Objection] = []
    proof_asset: ProofAssetConfig = ProofAssetConfig()


class Geography(Strict):
    country: str
    regions: list[str] = []
    timezone: str

    @field_validator("country")
    @classmethod
    def _iso2(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Z]{2}", value):
            raise ValueError("country must be an ISO 3166-1 alpha-2 code like IN or GB")
        return value

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown timezone {value!r}") from exc
        return value


class Segment(Strict):
    key: str
    industry: str
    size: str | None = None
    languages: str | None = None
    target_total: int = Field(default=50, ge=0)

    @field_validator("key")
    @classmethod
    def _key(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9_]+", value):
            raise ValueError("segment key must be lower-case letters, digits and underscores")
        return value


class Market(Strict):
    geographies: list[Geography] = Field(min_length=1)
    segments: list[Segment] = Field(min_length=1)
    b2b_or_b2c: Literal["b2b", "b2c"] = "b2b"
    exclude: list[str] = []

    @model_validator(mode="after")
    def _unique_segments(self) -> Market:
        keys = [s.key for s in self.segments]
        if len(keys) != len(set(keys)):
            raise ValueError("segment keys must be unique")
        return self


class ICP(Strict):
    must_have: list[str] = []
    nice_to_have: list[str] = []
    disqualifiers: list[str] = []
    signals: list[str] = []


class Channels(Strict):
    allowed: list[Channel] = ["email"]
    forbidden: list[Channel] = ["cold_call", "cold_sms", "cold_whatsapp"]
    copy_language: str = "en"
    tone: str = ""

    @model_validator(mode="after")
    def _never_cold(self) -> Channels:
        bad = NEVER_ALLOWED_CHANNELS.intersection(self.allowed)
        if bad:
            raise ValueError(f"these channels can never be allowed: {', '.join(sorted(bad))}")
        overlap = set(self.allowed).intersection(self.forbidden)
        if overlap:
            raise ValueError(f"channels both allowed and forbidden: {', '.join(sorted(overlap))}")
        return self


class Sender(Strict):
    from_name: str
    role: str
    business_phone: str | None = None
    postal_address: str
    mailboxes: list[str] = Field(min_length=1)

    @field_validator("mailboxes")
    @classmethod
    def _emails(cls, value: list[str]) -> list[str]:
        return [_check_email(item) for item in value]


class Constraints(Strict):
    monthly_budget_usd: float = Field(default=50, ge=0)
    daily_budget_usd: float | None = Field(default=None, ge=0)
    daily_new_prospects: int = Field(default=5, ge=0)
    approval: Literal["required"] = "required"
    test_mode_only_to: list[str] = []

    @field_validator("test_mode_only_to")
    @classmethod
    def _emails(cls, value: list[str]) -> list[str]:
        return [_check_email(item) for item in value]


class SpendGates(Strict):
    """Fit thresholds below which no money is spent on an account (design §5.4)."""

    paid_enrichment: int = Field(default=40, ge=0, le=100)
    dossier: int = Field(default=55, ge=0, le=100)
    proof_asset: int = Field(default=65, ge=0, le=100)
    drafting: int = Field(default=65, ge=0, le=100)


class Providers(Strict):
    discovery: list[str] = ["places_api", "csv_import"]
    crawl: list[str] = ["httpx_basic"]
    verify: list[str] = ["syntax_mx"]
    llm: list[str] = ["anthropic", "gemini"]
    allow_scraper: bool = False

    @model_validator(mode="after")
    def _scraper_opt_in(self) -> Providers:
        if "gmaps_scraper" in self.discovery and not self.allow_scraper:
            raise ValueError("gmaps_scraper needs providers.allow_scraper: true (Google ToS risk)")
        return self


class OfferConfig(Strict):
    offer: OfferSection
    market: Market
    icp: ICP = ICP()
    channels: Channels = Channels()
    sender: Sender
    constraints: Constraints = Constraints()
    spend_gates: SpendGates = SpendGates()
    providers: Providers = Providers()


def readiness_gaps(config: OfferConfig) -> list[str]:
    """Things that don't block validation but must be filled in before any real send."""
    gaps: list[str] = []
    if "todo" in config.sender.postal_address.lower():
        gaps.append("sender.postal_address is still a TODO")
    if not config.constraints.test_mode_only_to:
        gaps.append("constraints.test_mode_only_to is empty, so test mode delivers nothing")
    return gaps


class LoadedOffer(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    path: Path
    config: OfferConfig


class OfferConfigError(Exception):
    """offer.yaml is missing or invalid; the message is written for the operator."""


def _describe(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        where = ".".join(str(part) for part in err["loc"]) or "(top level)"
        lines.append(f"  - {where}: {err['msg']}")
    return "\n".join(lines)


def load_offer(offer_dir: Path) -> LoadedOffer:
    slug = offer_dir.name.lstrip("_")  # "_example" validates as "example"
    if not SLUG_RE.match(slug):
        raise OfferConfigError(
            f"{offer_dir}: folder name must be a slug (lower-case letters, digits, hyphens)"
        )
    path = offer_dir / "offer.yaml"
    if not path.is_file():
        raise OfferConfigError(f"{path}: not found")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise OfferConfigError(f"{path}: not valid YAML ({exc})") from exc
    try:
        config = OfferConfig.model_validate(raw)
    except ValidationError as exc:
        raise OfferConfigError(f"{path} has problems:\n{_describe(exc)}") from exc
    return LoadedOffer(slug=slug, path=path, config=config)


def offer_dirs(offers_dir: Path) -> list[Path]:
    """Offer folders, skipping ones that start with `_` or `.` (examples, templates)."""
    if not offers_dir.is_dir():
        return []
    return sorted(
        p
        for p in offers_dir.iterdir()
        if p.is_dir() and not p.name.startswith(("_", ".")) and (p / "offer.yaml").exists()
    )
