from pathlib import Path

import pytest

from si import evals
from si.cli import main
from tests.conftest import ROOT

CASES = sorted((ROOT / "evals").glob("*/cases/*.yaml"))


def test_there_are_cases() -> None:
    assert len(CASES) >= 3


@pytest.mark.parametrize("case", CASES, ids=lambda p: f"{p.parent.parent.name}/{p.stem}")
def test_case_passes_against_its_fixture(case: Path) -> None:
    fixture = evals.case_fixture(case, ROOT)
    assert fixture is not None, "every case names a committed fixture"
    failed = [o for o in evals.run_case(case, fixture) if not o.passed]
    assert failed == []


def test_case_fails_against_the_wrong_offer() -> None:
    case = ROOT / "evals" / "offer-intake" / "cases" / "voicesync-from-brief.yaml"
    outcomes = evals.run_case(case, ROOT / "offers" / "uk-webdesign-test")
    assert any(not o.passed for o in outcomes)


def test_invalid_offer_is_one_failed_outcome(tmp_path: Path) -> None:
    (tmp_path / "offer.yaml").write_text("offer: {}\n")
    case = tmp_path / "case.yaml"
    case.write_text("name: x\noffer: []\n")
    [outcome] = evals.run_case(case, tmp_path)
    assert not outcome.passed and outcome.check == "offer.yaml validates"


@pytest.mark.parametrize(
    ("rule", "passed"),
    [
        ({"path": "a.b", "equals": 1}, True),
        ({"path": "a.b", "equals": 2}, False),
        ({"path": "a.list", "contains": ["x"]}, True),
        ({"path": "a.list", "not_contains": "x"}, False),
        ({"path": "a.list.1", "one_of": ["y", "z"]}, True),
        ({"path": "a.text", "matches": r"^hel"}, True),
        ({"path": "a.empty", "empty": True}, True),
        ({"path": "a.nowhere", "empty": True}, True),
        ({"path": "a.nowhere", "present": False}, True),
        ({"path": "a.b", "present": True}, True),
        ({"path": "a.nowhere", "equals": 1}, False),
        ({"path": "a.b", "shrug": 1}, False),
    ],
)
def test_assertions(rule: dict[str, object], passed: bool) -> None:
    data = {"a": {"b": 1, "list": ["x", "y"], "text": "hello", "empty": []}}
    assert evals.check_assertion(data, rule).passed is passed


def test_cli_eval(capsys: pytest.CaptureFixture[str]) -> None:
    case = ROOT / "evals" / "strategy-pack" / "cases" / "uk-agency-pack.yaml"
    assert main(["eval", str(case), str(ROOT / "offers" / "uk-webdesign-test")]) == 0
    out = capsys.readouterr().out
    assert "FAIL" not in out and "checks passed" in out
