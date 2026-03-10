"""
LLM abstraction layer for Free_Guy backend.

Public API::

    from llm import LLMProvider, LLMConfig, get_provider, get_default_config

Provider implementations live in sub-modules (US-020, US-021):
    llm.openai_provider — OpenAIProvider
    llm.ollama_provider — OllamaProvider
"""

from llm.factory import get_default_config, get_provider
from llm.protocol import LLMConfig, LLMProvider

__all__ = [
    "LLMProvider",
    "LLMConfig",
    "get_provider",
    "get_default_config",
]
