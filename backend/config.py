"""Configuration for WarRoom."""

import os
from dotenv import load_dotenv

load_dotenv()

# Provider API keys. Direct OpenAI/Anthropic providers are scaffolded for a
# later migration and are not required by the current OpenRouter runtime path.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Direct provider model aliases. These defaults are intentionally centralized
# and easy to override because current model availability should be verified in
# the target account before relying on them.
OPENAI_PRIMARY_MODEL = os.getenv("OPENAI_PRIMARY_MODEL", "gpt-5.1")
OPENAI_FAST_MODEL = os.getenv("OPENAI_FAST_MODEL", "gpt-5-mini")
OPENROUTER_FREE_MODEL = os.getenv("OPENROUTER_FREE_MODEL", "openrouter/free")
CLAUDE_PRIMARY_MODEL = os.getenv("CLAUDE_PRIMARY_MODEL", "claude-sonnet-4-20250514")
CLAUDE_FAST_MODEL = os.getenv("CLAUDE_FAST_MODEL", "claude-3-5-haiku-20241022")


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default

# Provider configuration scaffold. OpenRouter remains enabled for the inherited
# ask/council/chairman flow until direct providers are implemented.
PROVIDERS = {
    "openrouter": {
        "enabled": True,
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": None,
    },
    "openai": {
        "enabled": bool(OPENAI_API_KEY),
        "api_key_env": "OPENAI_API_KEY",
        "default_model": OPENAI_PRIMARY_MODEL,
        "fast_model": OPENAI_FAST_MODEL,
    },
    "anthropic": {
        "enabled": bool(ANTHROPIC_API_KEY),
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": CLAUDE_PRIMARY_MODEL,
        "fast_model": CLAUDE_FAST_MODEL,
    },
}

MODEL_ALIASES = {
    "openai_primary": {
        "provider": "openai",
        "model": OPENAI_PRIMARY_MODEL,
        "display_name": "OpenAI Primary",
        "fallback_aliases": ["openai_fast"],
        "enabled": bool(OPENAI_API_KEY),
    },
    "openai_fast": {
        "provider": "openai",
        "model": OPENAI_FAST_MODEL,
        "display_name": "OpenAI Fast",
        "fallback_aliases": [],
        "enabled": bool(OPENAI_API_KEY),
    },
    "openrouter_free": {
        "provider": "openrouter",
        "model": OPENROUTER_FREE_MODEL,
        "display_name": "OpenRouter Free",
        "fallback_aliases": ["openai_fast"],
        "enabled": bool(OPENROUTER_API_KEY),
    },
    "claude_primary": {
        "provider": "anthropic",
        "model": CLAUDE_PRIMARY_MODEL,
        "display_name": "Claude Primary",
        "fallback_aliases": ["claude_fast", "openai_fast"],
        "enabled": bool(ANTHROPIC_API_KEY),
    },
    "claude_fast": {
        "provider": "anthropic",
        "model": CLAUDE_FAST_MODEL,
        "display_name": "Claude Fast",
        "fallback_aliases": ["openai_fast"],
        "enabled": bool(ANTHROPIC_API_KEY),
    },
}

RESPONDENT_MODEL_ALIASES = _csv_env(
    "WARROOM_RESPONDENT_MODELS",
    "openai_primary,openrouter_free",
)
REVIEWER_MODEL_ALIASES = _csv_env(
    "WARROOM_REVIEWER_MODELS",
    ",".join(RESPONDENT_MODEL_ALIASES),
)
SYNTHESIZER_MODEL_ALIAS = os.getenv("WARROOM_SYNTHESIZER_MODEL", "openai_fast")
TITLE_MODEL_ALIAS = os.getenv("WARROOM_TITLE_MODEL", "openai_fast")
FALLBACK_MODEL_ALIAS = os.getenv("WARROOM_FALLBACK_MODEL", "openai_fast")
PROVIDER_TIMEOUT_SECONDS = _float_env("WARROOM_PROVIDER_TIMEOUT_SECONDS", 60.0)

# Backward-compatible names for older code/docs. These now hold aliases, not
# raw provider model IDs.
COUNCIL_MODELS = RESPONDENT_MODEL_ALIASES
CHAIRMAN_MODEL = SYNTHESIZER_MODEL_ALIAS
TITLE_MODEL = TITLE_MODEL_ALIAS

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
