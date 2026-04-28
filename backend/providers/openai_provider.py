"""Direct OpenAI provider adapter."""

from time import perf_counter
from typing import Any

from ..config import OPENAI_API_KEY
from ..schemas.provider import ProviderRequest, ProviderResponse
from .base import Provider


class OpenAIProvider(Provider):
    """Provider adapter for direct OpenAI API calls."""

    name = "openai"

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        started = perf_counter()

        if not OPENAI_API_KEY:
            return ProviderResponse(
                provider=self.name,
                model=request.model,
                content="",
                error="OPENAI_API_KEY is not set",
                latency_ms=0,
            )

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            return ProviderResponse(
                provider=self.name,
                model=request.model,
                content="",
                error=f"OpenAI SDK is not installed: {exc}",
                latency_ms=0,
            )

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        params: dict[str, Any] = {
            "model": request.model,
            "input": request.user_prompt,
        }

        if request.system_prompt:
            params["instructions"] = request.system_prompt
        if request.temperature is not None and _supports_temperature(request.model):
            params["temperature"] = request.temperature
        if request.max_tokens is not None:
            params["max_output_tokens"] = request.max_tokens
        reasoning_effort = _reasoning_effort(request.model)
        if reasoning_effort:
            params["reasoning"] = {"effort": reasoning_effort}

        # response_format support differs between OpenAI endpoints and models.
        # Keep this adapter conservative for now and preserve the field for a
        # later structured-output pass.

        try:
            response = await client.responses.create(**params)
            latency_ms = int((perf_counter() - started) * 1000)
            usage = _extract_usage(response)
            raw = _extract_raw(response)

            return ProviderResponse(
                provider=self.name,
                model=getattr(response, "model", None) or request.model,
                content=_extract_text(response),
                raw=raw,
                latency_ms=latency_ms,
                usage=usage,
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
    """Extract visible text from an OpenAI Responses API object."""
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def _supports_temperature(model: str) -> bool:
    """Return whether to send temperature for the given model family."""
    # GPT-5 family models can reject temperature on the Responses API. Treat
    # temperature as a best-effort field and omit it for these defaults.
    return not _is_gpt5_family(model)


def _is_gpt5_family(model: str) -> bool:
    return model.startswith("gpt-5")


def _reasoning_effort(model: str) -> str | None:
    if model.startswith("gpt-5.1"):
        return "none"
    if model.startswith("gpt-5"):
        return "minimal"
    return None


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
            "status": data.get("status"),
            "object": data.get("object"),
        }
    return None
