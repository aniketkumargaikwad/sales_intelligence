"""Gemini free tier, used only as a fallback when Anthropic is unavailable (ADR-0005)."""

from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from si.checks.base import CheckResult
from si.config.settings import Settings
from si.llm.types import Completion, LLMRequest, Tier, Usage, describe
from si.registry import ProviderError

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider:
    name = "gemini"

    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self._http = http

    def configured(self) -> bool:
        return self.settings.gemini_api_key is not None

    def model_for(self, tier: Tier) -> str:
        return self.settings.gemini_model

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        key = self.settings.gemini_api_key
        if key is None:
            raise ProviderError("gemini is not configured")
        url = API.format(model=self.settings.gemini_model)
        headers = {"x-goog-api-key": key.get_secret_value()}
        try:
            if self._http is not None:
                response = await self._http.post(url, json=body, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=60) as http:
                    response = await http.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderError(f"connection failed: {describe(exc)}") from exc
        if response.status_code != 200:
            raise ProviderError(f"HTTP {response.status_code}: {describe(response.text)}")
        data: dict[str, Any] = response.json()
        return data

    async def complete_json(self, request: LLMRequest, schema: type[BaseModel]) -> Completion:
        schema_text = json.dumps(schema.model_json_schema())
        data = await self._post(
            {
                "systemInstruction": {
                    "parts": [
                        {
                            "text": f"{request.system}\n\nReply with JSON only, matching this "
                            f"JSON Schema:\n{schema_text}"
                        }
                    ]
                },
                "contents": [{"role": "user", "parts": [{"text": request.user}]}],
                "generationConfig": {
                    "maxOutputTokens": request.max_tokens,
                    "responseMimeType": "application/json",
                },
            }
        )
        meta = data.get("usageMetadata", {})
        usage = Usage(
            input_tokens=int(meta.get("promptTokenCount", 0)),
            output_tokens=int(meta.get("candidatesTokenCount", 0)),
        )
        model = self.settings.gemini_model
        candidates = data.get("candidates") or []
        if not candidates or candidates[0].get("finishReason") in {"SAFETY", "PROHIBITED_CONTENT"}:
            return Completion(self.name, model, usage, "refusal", None, refused=True)
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        try:
            parsed = schema.model_validate_json(text)
        except ValidationError as exc:
            return Completion(self.name, model, usage, "invalid", None, error=describe(exc))
        return Completion(self.name, model, usage, candidates[0].get("finishReason"), parsed)

    async def ping(self) -> CheckResult:
        component = "llm: gemini (fallback)"
        if not self.configured():
            return CheckResult.not_configured(component, "optional; set SI_GEMINI_API_KEY")
        try:
            await self._post(
                {
                    "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
                    "generationConfig": {"maxOutputTokens": 1},
                }
            )
        except ProviderError as exc:
            return CheckResult.failing(component, str(exc))
        return CheckResult.ok(component, f"1-token call to {self.settings.gemini_model} succeeded")
