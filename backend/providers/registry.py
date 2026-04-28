"""Provider registry and legacy-compatible query helpers."""

import asyncio
from typing import Any, Optional

from ..schemas.provider import ProviderRequest
from .base import Provider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .openrouter_provider import OpenRouterProvider


_PROVIDERS: dict[str, Provider] = {
    "openrouter": OpenRouterProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
}


def get_provider(name: str) -> Provider:
    """Resolve a provider adapter by name."""
    try:
        return _PROVIDERS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown provider: {name}") from exc


async def query_model(
    model: str,
    messages: list[dict[str, str]],
    timeout: float = 120.0,
    provider_name: str = "openrouter",
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> Optional[dict[str, Any]]:
    """Compatibility helper matching the old OpenRouter client shape."""
    provider = get_provider(provider_name)

    if hasattr(provider, "complete_messages"):
        response = await provider.complete_messages(model, messages, timeout=timeout)
    else:
        user_prompt = "\n\n".join(
            message["content"] for message in messages if message.get("role") != "system"
        )
        system_prompt = next(
            (message["content"] for message in messages if message.get("role") == "system"),
            None,
        )
        response = await provider.complete(
            ProviderRequest(
                provider=provider_name,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )

    if response.error:
        return None

    result: dict[str, Any] = {"content": response.content}
    if response.raw and "reasoning_details" in response.raw:
        result["reasoning_details"] = response.raw["reasoning_details"]
    return result


async def query_models_parallel(
    models: list[str],
    messages: list[dict[str, str]],
    provider_name: str = "openrouter",
) -> dict[str, Optional[dict[str, Any]]]:
    """Compatibility helper matching the old parallel query function."""
    tasks = [
        query_model(model, messages, provider_name=provider_name)
        for model in models
    ]
    responses = await asyncio.gather(*tasks)
    return {model: response for model, response in zip(models, responses)}
