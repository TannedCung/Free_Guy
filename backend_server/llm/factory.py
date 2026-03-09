"""
LLM provider factory.

Usage::

    from llm.factory import get_provider, get_default_config

    config = get_default_config()   # reads env vars
    provider = get_provider(config) # returns an LLMProvider instance
"""
from __future__ import annotations

import os

from llm.protocol import LLMConfig, LLMProvider

# ---------------------------------------------------------------------------
# Default configuration (env-driven)
# ---------------------------------------------------------------------------

_DEFAULT_PROVIDER = "ollama"
_DEFAULT_MODEL = "gemma2"
_DEFAULT_EMBEDDING_MODEL_OPENAI = "text-embedding-ada-002"
_DEFAULT_EMBEDDING_MODEL_OLLAMA = "nomic-embed-text"


def get_default_config() -> LLMConfig:
    """Build an :class:`LLMConfig` from environment variables.

    Environment variables (all optional with fallback defaults):

    * ``LLM_PROVIDER``         — ``"openai"`` | ``"ollama"`` (default: ``"ollama"``)
    * ``LLM_MODEL``            — chat model id (default: ``"gemma2"``)
    * ``LLM_BASE_URL``         — custom base URL (e.g. Ollama endpoint)
    * ``OPENAI_API_KEY``       — API key for OpenAI
    * ``EMBEDDING_PROVIDER``   — defaults to ``LLM_PROVIDER``
    * ``EMBEDDING_MODEL``      — embedding model id

    Returns:
        A fully populated :class:`LLMConfig`.
    """
    provider = os.environ.get("LLM_PROVIDER", _DEFAULT_PROVIDER).lower()
    model = os.environ.get("LLM_MODEL", _DEFAULT_MODEL)
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", "")

    embedding_provider = os.environ.get("EMBEDDING_PROVIDER", provider).lower()
    default_embed_model = (
        _DEFAULT_EMBEDDING_MODEL_OPENAI
        if embedding_provider == "openai"
        else _DEFAULT_EMBEDDING_MODEL_OLLAMA
    )
    embedding_model = os.environ.get("EMBEDDING_MODEL", default_embed_model)

    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
    )


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def get_provider(config: LLMConfig) -> LLMProvider:
    """Instantiate and return the :class:`LLMProvider` described by *config*.

    Currently supported providers:

    * ``"openai"``  — implemented in :mod:`llm.openai_provider`
    * ``"ollama"``  — implemented in :mod:`llm.ollama_provider`

    Args:
        config: Provider configuration.

    Returns:
        An :class:`LLMProvider` instance.

    Raises:
        ValueError: If *config.provider* is not a recognised provider name.
    """
    provider = config.provider.lower()

    if provider == "openai":
        from llm.openai_provider import OpenAIProvider
        return OpenAIProvider(config)

    if provider == "ollama":
        from llm.ollama_provider import OllamaProvider
        return OllamaProvider(config)

    raise ValueError(
        f"Unknown LLM provider: {config.provider!r}. "
        "Supported values: 'openai', 'ollama'."
    )
