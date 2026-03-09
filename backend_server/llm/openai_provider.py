"""
OpenAI LLM provider implementation.

Implements the LLMProvider protocol using the openai>=1.0 client API.

Usage::

    from llm import LLMConfig, get_provider

    config = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-...")
    provider = get_provider(config)
    reply = provider.chat([{"role": "user", "content": "Hello!"}])
"""
from __future__ import annotations

import logging
import time
from typing import Any

import openai
from openai import OpenAI

from llm.protocol import LLMConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry constants
# ---------------------------------------------------------------------------

_MAX_RETRIES = 5
_BASE_SLEEP_SECONDS = 1.0  # first back-off interval; doubles on each retry


class OpenAIProvider:
    """LLMProvider implementation backed by OpenAI's API (openai>=1.0).

    Satisfies the :class:`llm.protocol.LLMProvider` Protocol via structural
    subtyping — no explicit inheritance needed.

    Args:
        config: Provider configuration (model, api_key, base_url, …).
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._client = OpenAI(
            api_key=config.api_key or None,  # None → reads OPENAI_API_KEY env var
            base_url=config.base_url or None,  # None → default OpenAI endpoint
        )

    # ------------------------------------------------------------------
    # LLMProvider protocol methods
    # ------------------------------------------------------------------

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Generate a completion for a raw text prompt.

        Internally uses chat completions (``role=user``) because the legacy
        text-completion endpoint is not available for modern OpenAI models.

        Args:
            prompt: Raw text prompt.
            **kwargs: Override ``model``, ``temperature``, ``max_tokens``.

        Returns:
            The model's reply as a plain string.
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate a chat-style response.

        Args:
            messages: List of ``{"role": "...", "content": "..."}`` dicts.
            **kwargs: Override ``model``, ``temperature``, ``max_tokens``.

        Returns:
            The assistant's reply as a plain string.

        Raises:
            openai.OpenAIError: If all retries are exhausted.
        """
        model = kwargs.get("model", self._config.model)
        temperature = kwargs.get("temperature", self._config.temperature)
        max_tokens = kwargs.get("max_tokens", self._config.max_tokens)

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                logger.debug("[OpenAI chat] model=%s attempt=%d", model, attempt)
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content or ""
                logger.debug("[OpenAI chat] response=%s", content[:120])
                return content
            except openai.RateLimitError as exc:
                last_exc = exc
                sleep = _BASE_SLEEP_SECONDS * (2 ** attempt)
                logger.warning(
                    "[OpenAI chat] rate-limited on attempt %d, sleeping %.1fs",
                    attempt,
                    sleep,
                )
                time.sleep(sleep)
            except openai.APIConnectionError as exc:
                last_exc = exc
                sleep = _BASE_SLEEP_SECONDS * (2 ** attempt)
                logger.warning(
                    "[OpenAI chat] connection error on attempt %d, sleeping %.1fs: %s",
                    attempt,
                    sleep,
                    exc,
                )
                time.sleep(sleep)
            except openai.APIStatusError as exc:
                # 5xx server errors → retry; 4xx client errors → raise immediately
                if exc.status_code >= 500:
                    last_exc = exc
                    sleep = _BASE_SLEEP_SECONDS * (2 ** attempt)
                    logger.warning(
                        "[OpenAI chat] server error %d on attempt %d, sleeping %.1fs",
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
        """Return an embedding vector for *text*.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            openai.OpenAIError: If all retries are exhausted.
        """
        text = text.replace("\n", " ") or "this is blank"
        model = self._config.embedding_model or "text-embedding-ada-002"

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                logger.debug("[OpenAI embed] model=%s attempt=%d", model, attempt)
                response = self._client.embeddings.create(
                    input=[text],
                    model=model,
                )
                return response.data[0].embedding
            except openai.RateLimitError as exc:
                last_exc = exc
                sleep = _BASE_SLEEP_SECONDS * (2 ** attempt)
                logger.warning(
                    "[OpenAI embed] rate-limited on attempt %d, sleeping %.1fs",
                    attempt,
                    sleep,
                )
                time.sleep(sleep)
            except openai.APIConnectionError as exc:
                last_exc = exc
                sleep = _BASE_SLEEP_SECONDS * (2 ** attempt)
                logger.warning(
                    "[OpenAI embed] connection error on attempt %d, sleeping %.1fs: %s",
                    attempt,
                    sleep,
                    exc,
                )
                time.sleep(sleep)
            except openai.APIStatusError as exc:
                if exc.status_code >= 500:
                    last_exc = exc
                    sleep = _BASE_SLEEP_SECONDS * (2 ** attempt)
                    logger.warning(
                        "[OpenAI embed] server error %d on attempt %d, sleeping %.1fs",
                        exc.status_code,
                        attempt,
                        sleep,
                    )
                    time.sleep(sleep)
                else:
                    raise

        assert last_exc is not None
        raise last_exc
