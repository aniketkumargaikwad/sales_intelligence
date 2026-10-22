from dataclasses import dataclass

import pytest

from si.registry import AllProvidersFailed, NothingConfigured, ProviderError, Registry


@dataclass
class Fake:
    name: str
    ready: bool = True
    fails: bool = False

    def configured(self) -> bool:
        return self.ready


async def run(p: Fake) -> str:
    if p.fails:
        raise ProviderError("boom")
    return p.name


def registry(*providers: Fake) -> Registry[Fake]:
    r: Registry[Fake] = Registry("discovery")
    for p in providers:
        r.register(p)
    return r


async def test_uses_order_and_skips_unconfigured() -> None:
    r = registry(Fake("a", ready=False), Fake("b"), Fake("c"))
    served = await r.first(["a", "c", "b"], run)
    assert (served.value, served.provider) == ("c", "c")


async def test_error_falls_through() -> None:
    r = registry(Fake("a", fails=True), Fake("b"))
    assert (await r.first(["a", "b"], run)).provider == "b"


async def test_nothing_configured() -> None:
    r = registry(Fake("a", ready=False))
    with pytest.raises(NothingConfigured):
        await r.first(["a", "missing"], run)


async def test_all_failed_reports_each() -> None:
    r = registry(Fake("a", fails=True), Fake("b", fails=True))
    with pytest.raises(AllProvidersFailed) as exc:
        await r.first(["a", "b"], run)
    assert exc.value.errors == {"a": "boom", "b": "boom"}


def test_duplicate_registration() -> None:
    with pytest.raises(ValueError):
        registry(Fake("a"), Fake("a"))
