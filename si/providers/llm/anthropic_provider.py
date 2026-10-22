"""Anthropic API provider (ADR-0005). Default for every LLM task."""

from __future__ import annotations

from typing import Any

import anthropic
from pydantic import BaseModel, ValidationError

from si.checks.base import CheckResult
from si.config.settings import Settings
from si.llm.types import Completion, LLMRequest, Tier, Usage, describe
from si.registry import ProviderError


def _usage(raw: Any) -> Usage:
    return Usage(
        input_tokens=getattr(raw, "input_tokens", 0) or 0,
        output_tokens=getattr(raw, "output_tokens", 0) or 0,
        cache_read_tokens=getattr(raw, "cache_read_input_tokens", 0) or 0,
        cache_write_tokens=getattr(raw, "cache_creation_input_tokens", 0) or 0,
    )


def _text(message: Any) -> str:
    return "".join(block.text for block in message.content if block.type == "text")


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self._client = client

    def configured(self) -> bool:
        return self.settings.anthropic_api_key is not None or self._client is not None

    def model_for(self, tier: Tier) -> str:
        return self.settings.model_judgment if tier == "judgment" else self.settings.model_bulk

    @property
    def client(self) -> Any:
        if self._client is None:
            key = self.settings.anthropic_api_key
            self._client = anthropic.AsyncAnthropic(
                api_key=key.get_secret_value() if key else None, max_retries=2
            )
        return self._client

    async def complete_json(self, request: LLMRequest, schema: type[BaseModel]) -> Completion:
        model = self.model_for(request.tier)
        try:
            message = await self.client.messages.create(
                model=model,
                max_tokens=request.max_tokens,
                # The stable prefix (instructions + rules) is cached across items in a run.
                system=[
                    {"type": "text", "text": request.system, "cache_control": {"type": "ephemeral"}}
                ],
                messages=[{"role": "user", "content": request.user}],
                output_config={
                    "effort": request.effort,
                    "format": {
                        "type": "json_schema",
                        "schema": anthropic.transform_schema(schema),
                    },
                },
            )
        except anthropic.APIStatusError as exc:
            raise ProviderError(f"HTTP {exc.status_code}: {describe(exc.message)}") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError(f"connection failed: {describe(exc)}") from exc

        usage = _usage(message.usage)
        if message.stop_reason == "refusal":
            return Completion(self.name, model, usage, message.stop_reason, None, refused=True)
        try:
            parsed = schema.model_validate_json(_text(message))
        except ValidationError as exc:
            return Completion(
                self.name, model, usage, message.stop_reason, None, error=describe(exc)
            )
        return Completion(self.name, model, usage, message.stop_reason, parsed)

    async def ping(self) -> CheckResult:
        component = "llm: anthropic"
        if not self.configured():
            return CheckResult.not_configured(component, "set SI_ANTHROPIC_API_KEY")
        model = self.settings.model_bulk
        try:
            # A real 1-token completion is the only honest "is the key funded?" check.
            await self.client.messages.create(
                model=model,
                max_tokens=1,
                thinking={"type": "disabled"},
                messages=[{"role": "user", "content": "ping"}],
            )
        except anthropic.AuthenticationError:
            return CheckResult.failing(component, "API key was rejected")
        except anthropic.PermissionDeniedError as exc:
            return CheckResult.failing(component, f"key lacks permission: {describe(exc.message)}")
        except anthropic.APIStatusError as exc:
            if "credit" in str(exc.message).lower():
                return CheckResult.failing(component, "account has no credit; add funds")
            return CheckResult.failing(
                component, f"HTTP {exc.status_code}: {describe(exc.message)}"
            )
        except anthropic.APIConnectionError as exc:
            return CheckResult.failing(component, f"could not connect: {describe(exc)}")
        return CheckResult.ok(component, f"1-token call to {model} succeeded")
