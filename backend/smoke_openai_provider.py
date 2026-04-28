"""Smoke test for the direct OpenAI provider.

Run from the repo root:

    python -m backend.smoke_openai_provider

This does not print API keys.
"""

import asyncio

from .config import MODEL_ALIASES
from .providers.registry import get_provider
from .schemas.provider import ProviderRequest


async def main() -> None:
    provider = get_provider("openai")
    model = MODEL_ALIASES["openai_fast"]["model"]
    response = await provider.complete(
        ProviderRequest(
            provider="openai",
            model=model,
            system_prompt="You are a concise smoke-test assistant.",
            user_prompt="Reply with exactly: OpenAI provider OK",
            temperature=0.0,
            max_tokens=200,
        )
    )

    snippet = response.content[:200].replace("\n", " ")
    print(f"provider={response.provider}")
    print(f"model={response.model}")
    print(f"latency_ms={response.latency_ms}")
    print(f"error={response.error}")
    print(f"content={snippet}")


if __name__ == "__main__":
    asyncio.run(main())
