"""
LLM provider protocol and configuration dataclass.

Defines the structural interface (Protocol) that all LLM provider
implementations must satisfy, plus the LLMConfig dataclass used to
configure provider instances.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Provider-agnostic interface for LLM operations.

    Any class that implements these three methods satisfies this Protocol
    (structural subtyping — no inheritance required).
    """

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Generate a completion for a raw text prompt.

        Args:
            prompt: The raw text prompt.
            **kwargs: Provider-specific parameters (temperature, max_tokens, …).

        Returns:
            The model's text response.
        """
        ...

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate a chat-style response from a list of messages.

        Args:
            messages: List of ``{"role": "...", "content": "..."}`` dicts.
            **kwargs: Provider-specific parameters.

        Returns:
            The assistant's reply as a plain string.
        """
        ...

    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for *text*.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding.
        """
        ...


@dataclass
class LLMConfig:
    """Configuration for an LLM provider instance.

    Attributes:
        provider: Provider name — ``"openai"`` or ``"ollama"``.
        model: Chat/completion model identifier (e.g. ``"gpt-4o"``).
        api_key: API key for authenticated providers. Defaults to ``""``.
        base_url: Custom base URL (e.g. for Ollama or a proxy). Defaults to ``""``.
        embedding_provider: Provider to use for embeddings.
            Defaults to the same as *provider*.
        embedding_model: Embedding model identifier.
            Defaults to ``"text-embedding-ada-002"`` (OpenAI) or
            ``"nomic-embed-text"`` (Ollama).
        temperature: Sampling temperature. Defaults to ``0.0``.
        max_tokens: Maximum tokens in the response. Defaults to ``4096``.
    """

    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""
    embedding_provider: str = ""
    embedding_model: str = ""
    temperature: float = 0.0
    max_tokens: int = 4096

    def __post_init__(self) -> None:
        if not self.embedding_provider:
            self.embedding_provider = self.provider
