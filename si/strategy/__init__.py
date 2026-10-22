"""The strategy pack: `offers/<slug>/strategy/*.md` (brief §3, plan phase 2).

Claude writes the pack interactively with the operator (the `strategy-pack` skill). This module
is the deterministic half: it knows which documents a pack must have, which sections each one
needs, and lints the text so the pack can't smuggle a made-up price, customer or statistic into
the messaging that copy is later written from.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import yaml

from si.config.offer import LoadedOffer


@dataclass(frozen=True)
class DocSpec:
    key: str
    filename: str
    title: str
    sections: tuple[str, ...]


PACK: tuple[DocSpec, ...] = (
    DocSpec(
        "icp",
        "01-icp.md",
        "Ideal customer profile",
        (
            "Who buys",
            "Must have",
            "Nice to have",
            "Disqualifiers",
            "Signals to watch",
            "Where to find them",
        ),
    ),
    DocSpec(
        "personas",
        "02-personas.md",
        "Personas",
        ("Decision maker", "Day-to-day user", "What they care about", "What they fear"),
    ),
    DocSpec(
        "positioning",
        "03-positioning.md",
        "Positioning",
        ("For", "Who struggle with", "We are", "Unlike", "Because", "Alternatives they use today"),
    ),
    DocSpec(
        "messaging",
        "04-messaging-house.md",
        "Messaging house",
        ("Core message", "Pillars", "Proof we can use", "Things we never say", "Sample lines"),
    ),
    DocSpec(
        "objections",
        "05-objections.md",
        "Objection bank",
        ("Objections",),
    ),
    DocSpec(
        "channels",
        "06-channel-plan.md",
        "Channel plan",
        ("Allowed channels", "Forbidden channels", "Sequence outline", "Manual openers"),
    ),
    DocSpec(
        "funnel",
        "07-funnel.md",
        "Funnel",
        ("Stages", "Conversion targets", "What we measure"),
    ),
    DocSpec(
        "launch",
        "08-launch-30-days.md",
        "30-day launch plan",
        ("Week 1", "Week 2", "Week 3", "Week 4", "Decisions needed"),
    ),
)

Level = Literal["error", "warning"]


@dataclass(frozen=True)
class Finding:
    level: Level
    file: str
    line: int
    message: str

    def render(self) -> str:
        where = f"{self.file}:{self.line}" if self.line else self.file
        return f"{self.level.upper():7} {where}  {self.message}"


def offer_hash(offer: LoadedOffer) -> str:
    """Short hash of offer.yaml, stamped into each doc so stale packs are noticed."""
    return hashlib.sha256(offer.path.read_bytes()).hexdigest()[:12]


FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)

MONEY = re.compile(
    r"(?:[₹£$€]\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:k|K|m|M|lakh|crore)\b)?"
    r"|\b(?:Rs\.?|INR|GBP|USD|EUR)\s?\d[\d,]*(?:\.\d+)?"
    r"|\b\d[\d,]*(?:\.\d+)?\s?(?:rupees|pounds|dollars|euros)\b)",
    re.I,
)
PERCENT = re.compile(r"\b\d+(?:\.\d+)?\s?%")
SOURCE_MARK = re.compile(
    r"\((?:assumption|estimate|to verify|source:[^)]+|design §[\d.]+)\)|\]\(https?://|https?://",
    re.I,
)
CUSTOMER_CLAIM = re.compile(
    r"\b(trusted by|our (?:happy )?(?:customers|clients) (?:include|love|say|like)|"
    r"customers like|clients like|clients include|case stud(?:y|ies) (?:with|from)|"
    r"used by \d|join \d+)",
    re.I,
)
HYPE = re.compile(
    r"\b(free|guarantee[ds]?|urgent|risk[- ]free|100\s?%|act now|limited time|best in class|"
    r"no\.? ?1|#1)\b",
    re.I,
)
FAKE_REPLY = re.compile(r"^\s*>\s*(?:subject:\s*)?(?:re|fwd?):", re.I)


def _normalise_money(text: str) -> str:
    return re.sub(r"[\s,]", "", text).lower()


def _allowed_amounts(offer: LoadedOffer) -> set[str]:
    price = offer.config.offer.price
    texts = [p for p in (price.from_, price.upfront, price.trial) if p]
    amounts = {_normalise_money(m.group(0)) for t in texts for m in MONEY.finditer(t)}
    # Our own budget is an internal number, not a price claim.
    budget = offer.config.constraints.monthly_budget_usd
    amounts.add(_normalise_money(f"${budget:g}"))
    return amounts


def _lint_lines(spec: DocSpec, text: str, offer: LoadedOffer) -> list[Finding]:
    findings: list[Finding] = []
    allowed = _allowed_amounts(offer)
    has_proof = bool(offer.config.offer.proof.customers or offer.config.offer.proof.case_studies)
    for number, line in enumerate(text.splitlines(), start=1):
        marked = bool(SOURCE_MARK.search(line))
        for match in MONEY.finditer(line):
            amount = _normalise_money(match.group(0))
            if amount not in allowed and not marked:
                findings.append(
                    Finding(
                        "error",
                        spec.filename,
                        number,
                        f"{match.group(0)!r} is not one of our prices (offer.price). Mark it "
                        "(assumption) or link a source if it is about the prospect.",
                    )
                )
        for match in PERCENT.finditer(line):
            if not marked:
                findings.append(
                    Finding(
                        "error",
                        spec.filename,
                        number,
                        f"{match.group(0)!r} needs a source link or an (assumption) mark",
                    )
                )
        if not has_proof and CUSTOMER_CLAIM.search(line):
            findings.append(
                Finding(
                    "error",
                    spec.filename,
                    number,
                    "claims customers or case studies, but offer.proof is empty",
                )
            )
        # Lines in block quotes are sample copy: the outbound honesty rules apply to them.
        if line.lstrip().startswith(">"):
            hype = HYPE.search(line)
            if hype:
                findings.append(
                    Finding(
                        "error",
                        spec.filename,
                        number,
                        f"sample copy uses banned word {hype.group(0)!r}",
                    )
                )
            if FAKE_REPLY.search(line):
                findings.append(
                    Finding("error", spec.filename, number, "sample copy fakes a reply (Re:/Fwd:)")
                )
    return findings


def check_doc(spec: DocSpec, path: Path, offer: LoadedOffer, current_hash: str) -> list[Finding]:
    if not path.is_file():
        return [Finding("error", spec.filename, 0, "missing")]
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []

    match = FRONT_MATTER.match(text)
    if not match:
        return [Finding("error", spec.filename, 1, "missing front matter (--- ... ---)")]
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        return [Finding("error", spec.filename, 1, f"front matter is not valid YAML: {exc}")]
    if not isinstance(meta, dict):
        return [Finding("error", spec.filename, 1, "front matter must be a mapping")]

    if meta.get("offer") != offer.slug:
        findings.append(
            Finding("error", spec.filename, 1, f"front matter offer is not {offer.slug!r}")
        )
    if meta.get("doc") != spec.key:
        findings.append(
            Finding("error", spec.filename, 1, f"front matter doc must be {spec.key!r}")
        )
    generated = meta.get("generated_on")
    if not isinstance(generated, date):
        findings.append(
            Finding("error", spec.filename, 1, "generated_on must be a date (YYYY-MM-DD)")
        )
    if str(meta.get("offer_yaml_hash", "")) != current_hash:
        findings.append(
            Finding(
                "warning",
                spec.filename,
                1,
                "offer.yaml changed since this was written; regenerate or re-stamp it",
            )
        )

    body = text[match.end() :]
    headings = {h.strip().lower() for h in re.findall(r"^##\s+(.+?)\s*$", body, re.M)}
    for section in spec.sections:
        if section.lower() not in headings:
            findings.append(Finding("error", spec.filename, 0, f"missing section '## {section}'"))

    offset = text[: match.end()].count("\n")
    for finding in _lint_lines(spec, body, offer):
        findings.append(
            Finding(finding.level, finding.file, finding.line + offset, finding.message)
        )
    return findings


def check_pack(offer: LoadedOffer) -> list[Finding]:
    strategy = offer.path.parent / "strategy"
    current = offer_hash(offer)
    findings: list[Finding] = []
    for spec in PACK:
        findings.extend(check_doc(spec, strategy / spec.filename, offer, current))
    return findings
