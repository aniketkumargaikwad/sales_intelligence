"""Sending-domain authentication: SPF, DKIM and DMARC (brief §1.10, Gmail/Yahoo sender rules)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable

import dns.exception
import dns.resolver

from si.checks.base import CheckResult

TxtLookup = Callable[[str], list[str]]


def txt_records(name: str) -> list[str]:
    try:
        answer = dns.resolver.resolve(name, "TXT", lifetime=10)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return []
    return [b"".join(r.strings).decode("utf-8", "replace") for r in answer]


def check_domain(
    domain: str, selectors: Iterable[str], lookup: TxtLookup = txt_records
) -> list[CheckResult]:
    results: list[CheckResult] = []

    spf = [r for r in lookup(domain) if r.lower().startswith("v=spf1")]
    if len(spf) == 1:
        results.append(CheckResult.ok(f"dns: {domain} SPF", spf[0]))
    elif not spf:
        results.append(CheckResult.failing(f"dns: {domain} SPF", "no SPF record (v=spf1 ...)"))
    else:
        results.append(CheckResult.failing(f"dns: {domain} SPF", "more than one SPF record"))

    dmarc = [r for r in lookup(f"_dmarc.{domain}") if r.lower().startswith("v=dmarc1")]
    if not dmarc:
        results.append(CheckResult.failing(f"dns: {domain} DMARC", "no DMARC record at _dmarc"))
    else:
        policy = next(
            (p.split("=", 1)[1].strip() for p in dmarc[0].split(";") if p.strip().startswith("p=")),
            "missing",
        )
        results.append(CheckResult.ok(f"dns: {domain} DMARC", f"policy {policy}"))

    found = [s for s in selectors if any("p=" in r for r in lookup(f"{s}._domainkey.{domain}"))]
    if found:
        results.append(CheckResult.ok(f"dns: {domain} DKIM", f"selector(s): {', '.join(found)}"))
    else:
        results.append(
            CheckResult.failing(
                f"dns: {domain} DKIM",
                "no DKIM key found for the usual selectors; set SI_DKIM_SELECTORS to yours",
            )
        )
    return results


async def check_domains(domains: Iterable[str], selectors: Iterable[str]) -> list[CheckResult]:
    selectors = list(selectors)
    results: list[CheckResult] = []
    for domain in sorted(set(domains)):
        try:
            results.extend(await asyncio.to_thread(check_domain, domain, selectors))
        except dns.exception.DNSException as exc:
            results.append(CheckResult.failing(f"dns: {domain}", f"lookup failed: {exc}"))
    return results
