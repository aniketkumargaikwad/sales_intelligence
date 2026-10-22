from si.config.settings import Settings
from si.llm.types import LLMProvider
from si.providers.llm.anthropic_provider import AnthropicProvider
from si.providers.llm.gemini_provider import GeminiProvider
from si.registry import Registry


def llm_registry(settings: Settings) -> Registry[LLMProvider]:
    registry: Registry[LLMProvider] = Registry("llm")
    registry.register(AnthropicProvider(settings))
    registry.register(GeminiProvider(settings))
    return registry


__all__ = ["AnthropicProvider", "GeminiProvider", "llm_registry"]
