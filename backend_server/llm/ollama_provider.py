"""
Ollama LLM provider implementation.

Implements the LLMProvider protocol using Ollama's OpenAI-compatible API for
chat completions and the native Ollama client for embeddings.

Usage::

    from llm import LLMConfig, get_provider

    config = LLMConfig(
        provider="ollama",
        model="gemma2",
        base_url="http://localhost:11434",
    )
    provider = get_provider(config)
    reply = provider.chat([{"role": "user", "content": "Hello!"}])
"""

from __future__ import annotations

import logging
import time
from typing import Any

from openai import APIConnectionError, APIStatusError, OpenAI

from llm.protocol import LLMConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry constants
# ---------------------------------------------------------------------------

_MAX_RETRIES = 5
_BASE_SLEEP_SECONDS = 1.0  # first back-off interval; doubles on each retry

_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider:
    """LLMProvider implementation backed by a local Ollama instance.

    Uses Ollama's OpenAI-compatible endpoint (``/v1``) for chat completions
    and the native Ollama HTTP API (via ``ollama._client.Client``) for
    embeddings.

    Satisfies the :class:`llm.protocol.LLMProvider` Protocol via structural
    subtyping — no explicit inheritance needed.

    Args:
        config: Provider configuration (model, base_url, embedding_model, …).
            Set ``config.base_url`` (or env var ``OLLAMA_BASE_URL``) to the
            Ollama host, e.g. ``"http://localhost:11434"``.
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        base_url = config.base_url or _DEFAULT_BASE_URL
        # Ollama exposes an OpenAI-compatible chat endpoint at <host>/v1
        self._client = OpenAI(
            base_url=f"{base_url.rstrip('/')}/v1",
            api_key="ollama",  # required by client, not used by Ollama
        )
        # Native client for embeddings (ollama Python package)
        from ollama._client import Client as OllamaClient  # type: ignore[import]

        self._ollama_client = OllamaClient(host=base_url)

    # ------------------------------------------------------------------
    # LLMProvider protocol methods
    # ------------------------------------------------------------------

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Generate a completion for a raw text prompt.

        Internally wraps :meth:`chat` with a single user message.

        Args:
            prompt: Raw text prompt.
            **kwargs: Override ``model``, ``temperature``, ``max_tokens``.

        Returns:
            The model's reply as a plain string.
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate a chat-style response using Ollama's OpenAI-compatible API.

        Args:
            messages: List of ``{"role": "...", "content": "..."}`` dicts.
            **kwargs: Override ``model``, ``temperature``, ``max_tokens``.

        Returns:
            The assistant's reply as a plain string.

        Raises:
            openai.APIConnectionError: If all retries are exhausted due to
                connection failures.
        """
        model = kwargs.get("model", self._config.model)
        temperature = kwargs.get("temperature", self._config.temperature)
        max_tokens = kwargs.get("max_tokens", self._config.max_tokens)

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                logger.debug("[Ollama chat] model=%s attempt=%d", model, attempt)
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content or ""
                logger.debug("[Ollama chat] response=%s", content[:120])
                return content
            except APIConnectionError as exc:
                last_exc = exc
                sleep = _BASE_SLEEP_SECONDS * (2**attempt)
                logger.warning(
                    "[Ollama chat] connection error on attempt %d, sleeping %.1fs: %s",
                    attempt,
                    sleep,
                    exc,
                )
                time.sleep(sleep)
            except APIStatusError as exc:
                # 5xx server errors → retry; 4xx client errors → raise immediately
                if exc.status_code >= 500:
                    last_exc = exc
                    sleep = _BASE_SLEEP_SECONDS * (2**attempt)
                    logger.warning(
                        "[Ollama chat] server error %d on attempt %d, sleeping %.1fs",
                        exc.status_code,
                        attempt,
                        sleep,
                    )
                    time.sleep(sleep)
                else:
                    raise

        assert last_exc is not None
        raise last_exc

    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for *text* using the Ollama native API.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            Exception: If the Ollama embedding call fails after retries.
        """
        text = text.replace("\n", " ") or "this is blank"
        model = self._config.embedding_model or "nomic-embed-text"

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                logger.debug("[Ollama embed] model=%s attempt=%d", model, attempt)
                response = self._ollama_client.embeddings(prompt=text, model=model)
                # ollama._client.Client.embeddings returns an object with .embedding
                embedding: list[float] = response["embedding"]
                return embedding
            except Exception as exc:
                last_exc = exc
                sleep = _BASE_SLEEP_SECONDS * (2**attempt)
                logger.warning(
                    "[Ollama embed] error on attempt %d, sleeping %.1fs: %s",
                    attempt,
                    sleep,
                    exc,
                )
                time.sleep(sleep)

        assert last_exc is not None
        raise last_exc
