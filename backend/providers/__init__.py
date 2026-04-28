"""Provider adapters for WarRoom."""

from .base import Provider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .openrouter_provider import OpenRouterProvider
from .model_registry import complete_with_alias, resolve_alias
from .registry import get_provider, query_model, query_models_parallel

__all__ = [
    "Provider",
    "AnthropicProvider",
    "OpenAIProvider",
    "OpenRouterProvider",
    "complete_with_alias",
    "resolve_alias",
    "get_provider",
    "query_model",
    "query_models_parallel",
]
