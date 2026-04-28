"""Model alias resolution and fallback execution."""

import asyncio
from typing import Any

from ..config import (
    FALLBACK_MODEL_ALIAS,
    MODEL_ALIASES,
    PROVIDER_TIMEOUT_SECONDS,
)
from ..schemas.provider import ProviderRequest, ProviderResponse
from .registry import get_provider


def resolve_alias(alias: str) -> dict[str, Any]:
    """Return the configured model entry for an alias."""
    try:
        return MODEL_ALIASES[alias]
    except KeyError as exc:
        raise ValueError(f"Unknown model alias: {alias}") from exc


def _fallback_chain(alias: str) -> list[str]:
    entry = resolve_alias(alias)
    fallbacks = list(entry.get("fallback_aliases") or [])
    if FALLBACK_MODEL_ALIAS and FALLBACK_MODEL_ALIAS != alias:
        fallbacks.append(FALLBACK_MODEL_ALIAS)

    seen: set[str] = set()
    chain: list[str] = []
    for fallback in fallbacks:
        if fallback not in seen:
            seen.add(fallback)
            chain.append(fallback)
    return chain


async def complete_with_alias(
    alias: str,
    user_prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
    response_format: str | None = None,
    timeout_seconds: float | None = None,
) -> ProviderResponse:
    """Complete a prompt with alias fallback and timeout handling."""
    timeout = timeout_seconds or PROVIDER_TIMEOUT_SECONDS
    attempted_aliases: list[str] = []
    fallback_reason: str | None = None
    aliases_to_try = [alias]
    visited: set[str] = set()
    last_response: ProviderResponse | None = None

    while aliases_to_try:
        current_alias = aliases_to_try.pop(0)
        if current_alias in visited:
            continue
        visited.add(current_alias)
        attempted_aliases.append(current_alias)

        try:
            entry = resolve_alias(current_alias)
        except ValueError as exc:
            last_response = _error_response(
                alias=alias,
                attempted_aliases=attempted_aliases,
                error=str(exc),
                fallback_used=current_alias != alias,
                fallback_reason=fallback_reason,
            )
            fallback_reason = str(exc)
            continue

        provider_name = entry.get("provider")
        model = entry.get("model")
        enabled = bool(entry.get("enabled"))

        if not enabled or not provider_name or not model:
            reason = f"Model alias '{current_alias}' is disabled or incomplete"
            last_response = _error_response(
                alias=alias,
                attempted_aliases=attempted_aliases,
                error=reason,
                requested_provider=provider_name,
                requested_model=model,
                fallback_used=current_alias != alias,
                fallback_reason=fallback_reason,
            )
            fallback_reason = reason
            aliases_to_try.extend(
                item for item in _fallback_chain(current_alias) if item not in visited
            )
            continue

        request = ProviderRequest(
            provider=provider_name,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

        try:
            provider = get_provider(provider_name)
            response = await asyncio.wait_for(provider.complete(request), timeout=timeout)
        except asyncio.TimeoutError:
            response = ProviderResponse(
                provider=provider_name,
                model=model,
                content="",
                error=f"Provider call timed out after {timeout:g}s",
            )
        except Exception as exc:
            response = ProviderResponse(
                provider=provider_name,
                model=model,
                content="",
                error=str(exc),
            )

        enriched = _with_alias_metadata(
            response=response,
            alias=alias,
            current_alias=current_alias,
            requested_provider=provider_name,
            requested_model=model,
            attempted_aliases=attempted_aliases,
            fallback_reason=fallback_reason,
        )
        last_response = enriched

        if not enriched.error and enriched.content.strip():
            return enriched

        reason = enriched.error or "Provider returned empty content"
        fallback_reason = reason
        aliases_to_try.extend(
            item for item in _fallback_chain(current_alias) if item not in visited
        )

    if last_response is not None:
        return last_response

    return _error_response(
        alias=alias,
        attempted_aliases=attempted_aliases,
        error=f"No provider attempts were available for alias '{alias}'",
    )


async def complete_aliases_parallel(
    aliases: list[str],
    user_prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> dict[str, ProviderResponse]:
    """Complete the same prompt for several aliases concurrently."""
    tasks = [
        complete_with_alias(
            alias,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        for alias in aliases
    ]
    responses = await asyncio.gather(*tasks)
    return {alias: response for alias, response in zip(aliases, responses)}


def response_metadata(response: ProviderResponse) -> dict[str, Any]:
    """Return metadata safe to include in persisted/displayed artifacts."""
    display_name = display_name_for_alias(response.requested_alias)
    actual_alias = _actual_alias(response)
    actual_display_name = display_name_for_alias(actual_alias)
    technical_name = technical_name_for(
        response.actual_provider or response.provider,
        response.actual_model or response.model,
    )
    requested_technical_name = technical_name_for(
        response.requested_provider,
        response.requested_model,
    )
    return {
        "display_name": display_name,
        "actual_display_name": actual_display_name,
        "technical_name": technical_name,
        "requested_alias": response.requested_alias,
        "requested_provider": response.requested_provider,
        "requested_model": response.requested_model,
        "requested_technical_name": requested_technical_name,
        "actual_provider": response.actual_provider,
        "actual_model": response.actual_model,
        "actual_alias": actual_alias,
        "fallback_used": response.fallback_used,
        "fallback_reason": response.fallback_reason,
        "attempted_aliases": response.attempted_aliases,
        "latency_ms": response.latency_ms,
        "usage": response.usage,
        "error": response.error,
    }


def display_model(response: ProviderResponse) -> str:
    """Return a stable model label for current UI compatibility."""
    return display_name_for_alias(response.requested_alias)


def display_name_for_alias(alias: str | None) -> str:
    """Return the configured display name for an alias."""
    if not alias:
        return "Unknown Model"
    try:
        entry = resolve_alias(alias)
    except ValueError:
        return alias.replace("_", " ").title()
    return entry.get("display_name") or alias.replace("_", " ").title()


def technical_name_for(provider: str | None, model: str | None) -> str | None:
    if not provider or not model:
        return None
    return f"{provider}/{model}"


def _actual_alias(response: ProviderResponse) -> str | None:
    if not response.attempted_aliases:
        return response.requested_alias
    if response.error:
        return response.attempted_aliases[-1]
    actual_provider = response.actual_provider or response.provider
    actual_model = response.actual_model or response.model
    for alias in reversed(response.attempted_aliases):
        try:
            entry = resolve_alias(alias)
        except ValueError:
            continue
        if entry.get("provider") == actual_provider and entry.get("model") == actual_model:
            return alias
    return response.attempted_aliases[-1]


def _with_alias_metadata(
    response: ProviderResponse,
    alias: str,
    current_alias: str,
    requested_provider: str,
    requested_model: str,
    attempted_aliases: list[str],
    fallback_reason: str | None,
) -> ProviderResponse:
    response.requested_alias = alias
    response.requested_provider = requested_provider
    response.requested_model = requested_model
    response.actual_provider = response.provider
    response.actual_model = response.model
    response.fallback_used = current_alias != alias
    response.fallback_reason = fallback_reason if response.fallback_used else None
    response.attempted_aliases = list(attempted_aliases)
    return response


def _error_response(
    alias: str,
    attempted_aliases: list[str],
    error: str,
    requested_provider: str | None = None,
    requested_model: str | None = None,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
) -> ProviderResponse:
    return ProviderResponse(
        provider=requested_provider or "unknown",
        model=requested_model or "unknown",
        content="",
        error=error,
        requested_alias=alias,
        requested_provider=requested_provider,
        requested_model=requested_model,
        actual_provider=requested_provider,
        actual_model=requested_model,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        attempted_aliases=list(attempted_aliases),
    )
