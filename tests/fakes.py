"""In-memory fakes for engine tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from si.checks.base import CheckResult
from si.llm.budget import Spend
from si.llm.types import Completion, LLMRequest, Tier, Usage


@dataclass
class FakeMeter:
    month: Decimal = Decimal(0)
    day: Decimal = Decimal(0)
    paused: bool = False
    pause_reasons: list[str] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)

    async def spend(self, offer_id: UUID, now: datetime) -> Spend:
        return Spend(self.month, self.day)

    async def is_paused(self, offer_id: UUID) -> bool:
        return self.paused

    async def pause(self, offer_id: UUID, reason: str) -> None:
        self.paused = True
        self.pause_reasons.append(reason)

    async def record(self, **kwargs: Any) -> None:
        self.records.append(kwargs)
        self.month += kwargs["usd"]
        self.day += kwargs["usd"]


@dataclass
class ScriptedLLM:
    """Returns the scripted outputs in order: a dict (valid JSON), "invalid", "refuse"."""

    name: str
    script: list[Any]
    ready: bool = True
    model: str = "claude-haiku-5-5"
    requests: list[LLMRequest] = field(default_factory=list)

    def configured(self) -> bool:
        return self.ready

    def model_for(self, tier: Tier) -> str:
        return self.model

    async def complete_json(self, request: LLMRequest, schema: type[BaseModel]) -> Completion:
        self.requests.append(request)
        step = self.script.pop(0)
        usage = Usage(input_tokens=1_000, output_tokens=100)
        if isinstance(step, Exception):
            raise step
        if step == "refuse":
            return Completion(self.name, self.model, usage, "refusal", None, refused=True)
        if step == "invalid":
            return Completion(self.name, self.model, usage, "end_turn", None, error="bad")
        return Completion(self.name, self.model, usage, "end_turn", schema.model_validate(step))

    async def ping(self) -> CheckResult:
        return CheckResult.ok(f"llm: {self.name}")
