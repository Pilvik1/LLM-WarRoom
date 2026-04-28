"""Provider request and response schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ProviderRequest(BaseModel):
    """Normalized request passed to a model provider."""

    provider: str
    model: str
    system_prompt: str | None = None
    user_prompt: str
    temperature: float = 0.2
    max_tokens: int | None = None
    response_format: str | None = None


class ProviderResponse(BaseModel):
    """Normalized response returned from a model provider."""

    provider: str
    model: str
    content: str
    raw: dict[str, Any] | None = None
    error: str | None = None
    latency_ms: int | None = None
    usage: dict[str, Any] | None = None
    requested_alias: str | None = None
    requested_provider: str | None = None
    requested_model: str | None = None
    actual_provider: str | None = None
    actual_model: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    attempted_aliases: list[str] = Field(default_factory=list)
