"""Direct Anthropic provider adapter."""

from time import perf_counter
from typing import Any

from ..config import ANTHROPIC_API_KEY
from ..schemas.provider import ProviderRequest, ProviderResponse
from .base import Provider


class AnthropicProvider(Provider):
    """Provider adapter for direct Anthropic Messages API calls."""

    name = "anthropic"

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        started = perf_counter()

        if not ANTHROPIC_API_KEY:
            return ProviderResponse(
                provider=self.name,
                model=request.model,
                content="",
                error="ANTHROPIC_API_KEY is not set",
                latency_ms=0,
            )

        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            return ProviderResponse(
                provider=self.name,
                model=request.model,
                content="",
                error=f"Anthropic SDK is not installed: {exc}",
                latency_ms=0,
            )

        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        params: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens or 1024,
            "messages": [{"role": "user", "content": request.user_prompt}],
        }

        if request.system_prompt:
            params["system"] = request.system_prompt
        if request.temperature is not None:
            params["temperature"] = request.temperature

        # Anthropic's Messages API does not use OpenAI-style response_format.
        # Keep the normalized field for later structured-output work.

        try:
            response = await client.messages.create(**params)
            latency_ms = int((perf_counter() - started) * 1000)

            return ProviderResponse(
                provider=self.name,
                model=getattr(response, "model", None) or request.model,
                content=_extract_text(response),
                raw=_extract_raw(response),
                error=None,
                latency_ms=latency_ms,
                usage=_extract_usage(response),
            )
        except Exception as exc:
            latency_ms = int((perf_counter() - started) * 1000)
            return ProviderResponse(
                provider=self.name,
                model=request.model,
                content="",
                error=str(exc),
                latency_ms=latency_ms,
            )


def _extract_text(response: Any) -> str:
    """Extract visible text from an Anthropic Messages response."""
    chunks: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def _extract_usage(response: Any) -> dict[str, Any] | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump(mode="json", exclude_none=True)
    if isinstance(usage, dict):
        return usage
    return None


def _extract_raw(response: Any) -> dict[str, Any] | None:
    if hasattr(response, "model_dump"):
        data = response.model_dump(mode="json", exclude_none=True)
        return {
            "id": data.get("id"),
            "model": data.get("model"),
            "role": data.get("role"),
            "stop_reason": data.get("stop_reason"),
            "type": data.get("type"),
        }
    return None
