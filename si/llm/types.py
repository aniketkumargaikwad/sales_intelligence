from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel

from si.checks.base import CheckResult

Tier = Literal["judgment", "bulk"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
        }


@dataclass(frozen=True)
class LLMRequest:
    tier: Tier
    system: str
    user: str
    max_tokens: int
    effort: Effort


@dataclass(frozen=True)
class Completion:
    """One provider response. `parsed` is None when the output did not match the schema."""

    provider: str
    model: str
    usage: Usage
    stop_reason: str | None
    parsed: BaseModel | None
    refused: bool = False
    error: str | None = None


class LLMProvider(Protocol):
    name: str

    def configured(self) -> bool: ...

    def model_for(self, tier: Tier) -> str: ...

    async def complete_json(self, request: LLMRequest, schema: type[BaseModel]) -> Completion: ...

    async def ping(self) -> CheckResult: ...


def describe(value: Any) -> str:
    text = str(value)
    return text if len(text) <= 200 else text[:197] + "..."
