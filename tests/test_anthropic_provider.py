from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
from pydantic import BaseModel

from si.config.settings import Settings
from si.llm.types import LLMRequest
from si.providers.llm.anthropic_provider import AnthropicProvider


class Out(BaseModel):
    label: str


class FakeMessages:
    def __init__(self, reply: Any) -> None:
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def message(text: str, stop: str = "end_turn") -> Any:
    return SimpleNamespace(
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text),
        ],
        stop_reason=stop,
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_read_input_tokens=3,
            cache_creation_input_tokens=None,
        ),
    )


def provider(reply: Any) -> tuple[AnthropicProvider, FakeMessages]:
    messages = FakeMessages(reply)
    return AnthropicProvider(Settings(), client=SimpleNamespace(messages=messages)), messages


REQUEST = LLMRequest(tier="judgment", system="sys", user="usr", max_tokens=100, effort="high")


async def test_structured_request_shape() -> None:
    p, messages = provider(message('{"label": "ok"}'))
    completion = await p.complete_json(REQUEST, Out)
    assert completion.parsed == Out(label="ok")
    assert completion.usage.cache_read_tokens == 3
    call = messages.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert call["output_config"]["effort"] == "high"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert "thinking" not in call


async def test_invalid_json_is_reported_not_raised() -> None:
    p, _ = provider(message("not json"))
    completion = await p.complete_json(REQUEST, Out)
    assert completion.parsed is None and completion.error


async def test_refusal() -> None:
    p, _ = provider(message("", stop="refusal"))
    assert (await p.complete_json(REQUEST, Out)).refused


async def test_ping_reports_unfunded_account() -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(400, request=request)
    error = anthropic.BadRequestError(
        "Your credit balance is too low", response=response, body=None
    )
    p, messages = provider(error)
    result = await p.ping()
    assert result.status == "failing" and "no credit" in result.detail
    assert messages.calls[0]["max_tokens"] == 1


async def test_ping_ok_and_not_configured() -> None:
    p, _ = provider(message("p"))
    assert (await p.ping()).status == "ok"
    assert (await AnthropicProvider(Settings()).ping()).status == "not_configured"
