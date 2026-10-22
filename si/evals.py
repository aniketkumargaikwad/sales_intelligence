"""Eval cases for LLM-backed skills (brief §10): golden input → expected properties.

A case (`evals/<skill>/cases/*.yaml`) holds the operator input a skill was given and the
properties its output must have. `si eval <case> <offer-folder>` checks an output against the
case; the test suite runs every case against its committed `fixture` so the expectations
themselves stay honest.

    name: short-id
    skill: offer-intake
    input: |            # what the operator said / provided
      ...
    fixture: offers/voicesync
    offer:              # assertions on offer.yaml (dotted paths into the raw YAML)
      - {path: offer.price.from, equals: "₹2,499/month"}
      - {path: offer.proof.customers, empty: true}
    strategy:           # optional: assertions on the strategy pack
      clean: true
      mentions: {icp: ["Companies House"]}
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from si import strategy
from si.config.offer import OfferConfigError, load_offer

MISSING = object()


@dataclass(frozen=True)
class Outcome:
    passed: bool
    check: str
    detail: str = ""


def resolve(data: Any, path: str) -> Any:
    node = data
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return MISSING
    return node


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return [value]


def check_assertion(data: Any, rule: dict[str, Any]) -> Outcome:
    path = rule["path"]
    value = resolve(data, path)
    label = f"{path} " + ", ".join(f"{k}={v!r}" for k, v in rule.items() if k != "path")
    if "present" in rule:
        ok = (value is not MISSING and value not in (None, "", [])) == bool(rule["present"])
        return Outcome(
            ok, label, "" if ok else f"got {value if value is not MISSING else 'nothing'!r}"
        )
    if value is MISSING:
        if rule.get("empty") is True:
            return Outcome(True, label)
        return Outcome(False, label, "path not found")
    if "equals" in rule:
        ok = value == rule["equals"]
    elif "empty" in rule:
        ok = (value in (None, "", [], {})) == bool(rule["empty"])
    elif "contains" in rule:
        ok = all(item in _as_list(value) for item in _as_list(rule["contains"]))
    elif "not_contains" in rule:
        ok = not any(item in _as_list(value) for item in _as_list(rule["not_contains"]))
    elif "one_of" in rule:
        ok = value in rule["one_of"]
    elif "matches" in rule:
        ok = isinstance(value, str) and re.search(rule["matches"], value) is not None
    else:
        return Outcome(False, label, "unknown assertion")
    return Outcome(ok, label, "" if ok else f"got {value!r}")


def run_case(case_path: Path, offer_dir: Path) -> list[Outcome]:
    case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    outcomes: list[Outcome] = []
    try:
        offer = load_offer(offer_dir)
    except OfferConfigError as exc:
        return [Outcome(False, "offer.yaml validates", str(exc))]
    outcomes.append(Outcome(True, "offer.yaml validates"))

    raw = yaml.safe_load(offer.path.read_text(encoding="utf-8"))
    for rule in case.get("offer", []):
        outcomes.append(check_assertion(raw, rule))

    pack_rules = case.get("strategy")
    if pack_rules:
        findings = strategy.check_pack(offer)
        if pack_rules.get("clean"):
            errors = [f for f in findings if f.level == "error"]
            outcomes.append(
                Outcome(
                    not errors,
                    "strategy pack has no errors",
                    "; ".join(f.render() for f in errors[:5]),
                )
            )
        docs = {spec.key: spec for spec in strategy.PACK}
        for key, phrases in (pack_rules.get("mentions") or {}).items():
            path = offer.path.parent / "strategy" / docs[key].filename
            text = path.read_text(encoding="utf-8").lower() if path.is_file() else ""
            for phrase in phrases:
                outcomes.append(
                    Outcome(phrase.lower() in text, f"{docs[key].filename} mentions {phrase!r}")
                )
    return outcomes


def case_fixture(case_path: Path, root: Path) -> Path | None:
    case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    fixture = case.get("fixture")
    return root / fixture if fixture else None
