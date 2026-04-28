"""Smoke test for the direct Anthropic provider.

Run from the repo root:

    python -m backend.smoke_anthropic_provider

This does not print API keys. Missing keys and account-credit errors are
reported clearly because Anthropic is optional during migration.
"""

import asyncio

from .config import ANTHROPIC_API_KEY, MODEL_ALIASES
from .providers.registry import get_provider
from .schemas.provider import ProviderRequest


async def main() -> None:
    if not ANTHROPIC_API_KEY:
        print("ANTHROPIC_API_KEY is not set; Anthropic provider smoke test skipped.")
        return

    provider = get_provider("anthropic")
    model = MODEL_ALIASES["claude_fast"]["model"]
    response = await provider.complete(
        ProviderRequest(
            provider="anthropic",
            model=model,
            system_prompt="You are a concise smoke-test assistant.",
            user_prompt="Reply with exactly: Anthropic provider OK",
            temperature=0.0,
            max_tokens=200,
        )
    )

    snippet = response.content[:200].replace("\n", " ")
    print(f"provider={response.provider}")
    print(f"model={response.model}")
    print(f"latency_ms={response.latency_ms}")
    print(f"error={_friendly_error(response.error)}")
    print(f"content={snippet}")


def _friendly_error(error: str | None) -> str | None:
    if not error:
        return None
    lowered = error.lower()
    soft_failures = [
        "credit",
        "payment",
        "billing",
        "rate limit",
        "rate_limit",
        "quota",
        "overloaded",
    ]
    if any(item in lowered for item in soft_failures):
        return f"{error} (Anthropic account availability issue; provider code loaded.)"
    return error


if __name__ == "__main__":
    asyncio.run(main())
