"""`python -m si <task>`. Tasks arrive phase by phase (docs/plan.md)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from si import __version__, evals, strategy
from si.checks import run as checks
from si.config.offer import OfferConfigError, load_offer, offer_dirs
from si.config.settings import load_settings
from si.db import migrate as migrations
from si.db.connection import DatabaseNotConfigured, connect
from si.providers.llm import llm_registry


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m si", description="sales-intelligence engine")
    parser.add_argument("--version", action="version", version=f"si {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logs")
    sub = parser.add_subparsers(dest="task", required=True)

    sub.add_parser("migrate", help="apply pending database migrations")

    check = sub.add_parser("check", help="test every configured piece with a real minimal call")
    check.add_argument(
        "--only", action="append", choices=checks.GROUPS, help="run only these groups (repeatable)"
    )
    check.add_argument("--json", action="store_true", help="machine-readable output")
    check.add_argument(
        "--skip-if-unconfigured",
        action="store_true",
        help="exit 0 without checking when the database is not configured (scheduled keep-alive)",
    )

    strategy = sub.add_parser("strategy", help="check an offer's strategy pack")
    strategy.add_argument("action", choices=["check", "hash"])
    strategy.add_argument("offer", type=Path, help="offer folder, e.g. offers/voicesync")

    evaluate = sub.add_parser("eval", help="check a skill's output against an eval case")
    evaluate.add_argument("case", type=Path, help="evals/<skill>/cases/<name>.yaml")
    evaluate.add_argument("offer", type=Path, help="offer folder the skill produced")

    validate = sub.add_parser("validate", help="validate offers/<slug>/offer.yaml files")
    validate.add_argument("paths", nargs="*", type=Path, help="offer folders (default: all)")
    return parser


async def _migrate() -> int:
    settings = load_settings()
    try:
        async with connect(settings) as conn:
            applied = await migrations.migrate(conn)
    except DatabaseNotConfigured as exc:
        print(f"skipping migrate: {exc}")
        return 1
    except migrations.MigrationError as exc:
        print(f"migration problem: {exc}", file=sys.stderr)
        return 1
    if applied:
        for m in applied:
            print(f"applied {m.path.name}")
    else:
        print("schema already up to date")
    return 0


async def _check(only: list[str] | None, as_json: bool, skip_if_unconfigured: bool) -> int:
    settings = load_settings()
    if skip_if_unconfigured and settings.database_url is None:
        print("skipping check: SI_DATABASE_URL is not configured")
        return 0
    results = await checks.run_checks(
        settings,
        llm_providers=llm_registry(settings).all(),
        only=set(only) if only else None,
    )
    print(checks.render_json(results) if as_json else checks.render(results))
    return checks.exit_code(results)


def _validate(paths: list[Path]) -> int:
    settings = load_settings()
    targets = paths or offer_dirs(settings.offers_dir)
    if not targets:
        print(f"no offers found in {settings.offers_dir}/")
        return 0
    failed = 0
    for path in targets:
        try:
            offer = load_offer(path)
        except OfferConfigError as exc:
            failed += 1
            print(f"FAIL {exc}")
        else:
            print(f"ok   {offer.slug}: {offer.config.offer.name}")
    return 1 if failed else 0


def _strategy(action: str, folder: Path) -> int:
    try:
        offer = load_offer(folder)
    except OfferConfigError as exc:
        print(f"FAIL {exc}")
        return 1
    if action == "hash":
        print(strategy.offer_hash(offer))
        return 0
    findings = strategy.check_pack(offer)
    for finding in findings:
        print(finding.render())
    errors = sum(f.level == "error" for f in findings)
    warnings = len(findings) - errors
    print(
        f"{offer.slug}: strategy pack has {errors} error(s), {warnings} warning(s)"
        if findings
        else f"{offer.slug}: strategy pack is complete and clean"
    )
    return 1 if errors else 0


def _eval(case: Path, folder: Path) -> int:
    outcomes = evals.run_case(case, folder)
    for outcome in outcomes:
        mark = "pass" if outcome.passed else "FAIL"
        print(f"{mark}  {outcome.check}" + (f"  ({outcome.detail})" if outcome.detail else ""))
    failed = sum(not o.passed for o in outcomes)
    print(f"{case.stem}: {len(outcomes) - failed}/{len(outcomes)} checks passed")
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    if args.task == "migrate":
        return asyncio.run(_migrate())
    if args.task == "check":
        return asyncio.run(_check(args.only, args.json, args.skip_if_unconfigured))
    if args.task == "strategy":
        return _strategy(args.action, args.offer)
    if args.task == "eval":
        return _eval(args.case, args.offer)
    if args.task == "validate":
        return _validate(args.paths)
    raise AssertionError(f"unhandled task {args.task}")
