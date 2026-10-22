"""Provider registry (design §5.2).

Every external capability is a provider with a name and a `configured()` check. Each offer
lists a fallback order per capability. Unconfigured providers are skipped with a log line;
a provider error falls through to the next one; if nothing is configured the caller gets
`NothingConfigured` and should exit cleanly ("skipping: not configured").
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

log = logging.getLogger("si.registry")


class Provider(Protocol):
    name: str

    def configured(self) -> bool: ...


P = TypeVar("P", bound=Provider)
R = TypeVar("R")


class ProviderError(Exception):
    """A provider failed for this item; the next provider in the chain should be tried."""


class NothingConfigured(Exception):
    """No provider in the chain is configured. Callers skip the step and exit 0."""


class AllProvidersFailed(Exception):
    def __init__(self, capability: str, errors: dict[str, str]) -> None:
        self.capability = capability
        self.errors = errors
        detail = "; ".join(f"{name}: {msg}" for name, msg in errors.items())
        super().__init__(f"every {capability} provider failed ({detail})")


@dataclass(frozen=True)
class Served(Generic[R]):
    value: R
    provider: str


class Registry(Generic[P]):
    def __init__(self, capability: str) -> None:
        self.capability = capability
        self._providers: dict[str, P] = {}

    def register(self, provider: P) -> None:
        if provider.name in self._providers:
            raise ValueError(f"{self.capability} provider {provider.name!r} registered twice")
        self._providers[provider.name] = provider

    def get(self, name: str) -> P | None:
        return self._providers.get(name)

    def all(self) -> list[P]:
        return list(self._providers.values())

    def names(self) -> list[str]:
        return sorted(self._providers)

    def chain(self, order: Iterable[str]) -> list[P]:
        """The configured providers in `order`, logging why each other one is skipped."""
        ready: list[P] = []
        for name in order:
            provider = self._providers.get(name)
            if provider is None:
                log.warning("skipping %s %s: no such provider", self.capability, name)
            elif not provider.configured():
                log.info("skipping %s %s: not configured", self.capability, name)
            else:
                ready.append(provider)
        return ready

    async def first(self, order: Iterable[str], call: Callable[[P], Awaitable[R]]) -> Served[R]:
        """Run `call` on each configured provider in order until one succeeds."""
        providers = self.chain(order)
        if not providers:
            raise NothingConfigured(f"no {self.capability} provider is configured")
        errors: dict[str, str] = {}
        for provider in providers:
            try:
                return Served(await call(provider), provider.name)
            except ProviderError as exc:
                log.warning("%s %s failed, trying next: %s", self.capability, provider.name, exc)
                errors[provider.name] = str(exc)
        raise AllProvidersFailed(self.capability, errors)
