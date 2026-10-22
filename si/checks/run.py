"""`si check`: prove every configured piece works with a real, minimal call (design §5.2)."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Iterable, Sequence

from si.checks.base import CheckResult
from si.checks.dns import check_domains
from si.config.offer import (
    LoadedOffer,
    OfferConfigError,
    load_offer,
    offer_dirs,
    readiness_gaps,
)
from si.config.settings import Settings
from si.db import migrate as migrations
from si.db.connection import DatabaseNotConfigured, connect
from si.llm.types import LLMProvider, describe
from si.providers.mail.login import check_imap, check_smtp

GROUPS = ("config", "send_mode", "database", "llm", "mail", "dns")

DnsCheck = Callable[[Iterable[str], Iterable[str]], Awaitable[list[CheckResult]]]


def load_offers(settings: Settings) -> tuple[list[LoadedOffer], list[CheckResult]]:
    offers: list[LoadedOffer] = []
    results: list[CheckResult] = []
    dirs = offer_dirs(settings.offers_dir)
    if not dirs:
        results.append(
            CheckResult.info("config: offers", f"no offers yet in {settings.offers_dir}/ (phase 2)")
        )
    for directory in dirs:
        try:
            offer = load_offer(directory)
        except OfferConfigError as exc:
            results.append(CheckResult.failing(f"config: {directory.name}", str(exc)))
        else:
            offers.append(offer)
            results.append(CheckResult.ok(f"config: {offer.slug}", "offer.yaml is valid"))
            for gap in readiness_gaps(offer.config):
                results.append(CheckResult.info(f"config: {offer.slug}", f"before go-live: {gap}"))
    return offers, results


def send_mode(settings: Settings, offers: Sequence[LoadedOffer]) -> CheckResult:
    if not settings.test_mode:
        return CheckResult.info("send mode", "LIVE: approved messages go to real recipients")
    allow = sorted(
        set(settings.only_to).union(*(o.config.constraints.test_mode_only_to for o in offers))
    )
    if not allow:
        return CheckResult.info(
            "send mode", "TEST MODE: nothing is delivered (allow-list is empty)"
        )
    return CheckResult.info("send mode", f"TEST MODE: only {', '.join(allow)} can receive mail")


async def database(settings: Settings) -> CheckResult:
    component = "database"
    try:
        async with connect(settings) as conn:
            version = await conn.fetchval("show server_version")
            state = await migrations.status(conn)
    except DatabaseNotConfigured:
        return CheckResult.failing(component, "SI_DATABASE_URL is not set")
    except migrations.MigrationError as exc:
        return CheckResult.failing(component, str(exc))
    except Exception as exc:  # any driver or network error is a failed check, not a crash
        return CheckResult.failing(component, f"could not connect: {describe(exc)}")
    if state.pending:
        names = ", ".join(m.path.name for m in state.pending)
        return CheckResult.failing(
            component,
            f"Postgres {version}; {len(state.pending)} pending migration(s): {names}. "
            "Run: python -m si migrate",
        )
    return CheckResult.ok(
        component, f"Postgres {version}; schema up to date ({len(state.applied)} migrations)"
    )


def sending_domains(offers: Sequence[LoadedOffer]) -> set[str]:
    return {box.split("@", 1)[1] for o in offers for box in o.config.sender.mailboxes}


async def run_checks(
    settings: Settings,
    *,
    llm_providers: Sequence[LLMProvider],
    only: set[str] | None = None,
    dns_check: DnsCheck = check_domains,
) -> list[CheckResult]:
    wanted = only if only else set(GROUPS)
    offers, results = load_offers(settings)
    if "config" not in wanted:
        results = []
    if "send_mode" in wanted:
        results.append(send_mode(settings, offers))
    if "database" in wanted:
        results.append(await database(settings))
    if "llm" in wanted:
        for provider in llm_providers:
            results.append(await provider.ping())
    if "mail" in wanted:
        results.append(await check_smtp(settings))
        results.append(await check_imap(settings))
    if "dns" in wanted:
        domains = sending_domains(offers)
        if domains:
            results.extend(await dns_check(domains, settings.dkim_selectors))
        else:
            results.append(CheckResult.info("dns", "no sending domains yet (set sender.mailboxes)"))
    return results


SYMBOL = {"ok": "ok  ", "not_configured": "--  ", "failing": "FAIL", "info": "info"}


def render(results: Sequence[CheckResult]) -> str:
    width = max((len(r.component) for r in results), default=10)
    lines = [f"{SYMBOL[r.status]}  {r.component.ljust(width)}  {r.detail}" for r in results]
    failing = sum(r.status == "failing" for r in results)
    missing = sum(r.status == "not_configured" for r in results)
    lines.append("")
    lines.append(
        f"{failing} failing, {missing} not configured, "
        f"{sum(r.status == 'ok' for r in results)} working."
    )
    return "\n".join(lines)


def render_json(results: Sequence[CheckResult]) -> str:
    return json.dumps(
        [{"component": r.component, "status": r.status, "detail": r.detail} for r in results],
        indent=2,
    )


def exit_code(results: Sequence[CheckResult]) -> int:
    return 1 if any(r.status == "failing" for r in results) else 0
