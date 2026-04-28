"""OpenRouter provider adapter.

This adapter deliberately calls the existing OpenRouter client so the current
runtime behavior is preserved while the provider abstraction is introduced.
"""

from time import perf_counter
from typing import Any

from .. import openrouter
from ..schemas.provider import ProviderRequest, ProviderResponse
from .base import Provider


class OpenRouterProvider(Provider):
    """Provider adapter for the inherited OpenRouter runtime path."""

    name = "openrouter"

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})
        return await self.complete_messages(request.model, messages)

    async def complete_messages(
        self,
        model: str,
        messages: list[dict[str, str]],
        timeout: float = 120.0,
    ) -> ProviderResponse:
        started = perf_counter()
        response = await openrouter.query_model(model, messages, timeout=timeout)
        latency_ms = int((perf_counter() - started) * 1000)

        if response is None:
            return ProviderResponse(
                provider=self.name,
                model=model,
                content="",
                error="OpenRouter request failed",
                latency_ms=latency_ms,
            )

        raw: dict[str, Any] = {}
        if response.get("reasoning_details") is not None:
            raw["reasoning_details"] = response.get("reasoning_details")

        return ProviderResponse(
            provider=self.name,
            model=model,
            content=response.get("content") or "",
            raw=raw or None,
            latency_ms=latency_ms,
        )
