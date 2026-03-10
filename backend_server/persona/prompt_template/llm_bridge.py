"""
LLM provider bridge — drop-in replacements for ollama_structure functions.

All prompt modules and cognitive modules should import LLM-related functions
from this module instead of directly from ollama_structure or gpt_structure.
Switching the underlying LLM provider requires only environment variable
changes (LLM_PROVIDER, LLM_MODEL, EMBEDDING_PROVIDER, EMBEDDING_MODEL, etc.).

Non-LLM utilities (generate_prompt for template file I/O) are also provided here
so callers only need one import location.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Callable, Optional

from llm.factory import get_default_config, get_provider
from llm.protocol import LLMProvider

# ---------------------------------------------------------------------------
# Non-LLM utility — copied from ollama_structure to avoid importing that
# module at startup (it has heavy dependencies: openai, ollama).
# ---------------------------------------------------------------------------


def generate_prompt(curr_input: Any, prompt_lib_file: str) -> str:
    """Load a prompt template file and substitute ``!<INPUT N>!`` placeholders.

    Pure file I/O — no LLM call is made here.

    Args:
        curr_input: A single string or a list of strings to substitute.
        prompt_lib_file: Path to the ``.txt`` template file.

    Returns:
        The rendered prompt string with all placeholders replaced.
    """
    if isinstance(curr_input, str):
        curr_input = [curr_input]
    curr_input = [str(i) for i in curr_input]

    with open(prompt_lib_file, "r") as f:
        prompt = f.read()

    for count, value in enumerate(curr_input):
        prompt = prompt.replace(f"!<INPUT {count}>!", value)

    if "<commentblockmarker>###</commentblockmarker>" in prompt:
        prompt = prompt.split("<commentblockmarker>###</commentblockmarker>")[1]

    return prompt.strip()


# ---------------------------------------------------------------------------
# Module-level provider singleton (lazy-initialised, thread-safe)
# ---------------------------------------------------------------------------

_provider: Optional[LLMProvider] = None
_provider_lock = threading.Lock()


def _get_provider() -> LLMProvider:
    """Return the module-level LLMProvider, initialising it on first call."""
    global _provider
    if _provider is None:
        with _provider_lock:
            if _provider is None:
                _provider = get_provider(get_default_config())
    return _provider


def set_provider(provider: LLMProvider) -> None:
    """Replace the module-level provider (useful for testing / dependency injection)."""
    global _provider
    with _provider_lock:
        _provider = provider


# ---------------------------------------------------------------------------
# Public API — same call signatures as the functions in ollama_structure.py
# ---------------------------------------------------------------------------


def ChatGPT_single_request(prompt: str) -> str:
    """Send a single prompt and return the raw string response."""
    return _get_provider().complete(prompt)


def safe_generate_response(
    prompt: str,
    gpt_param: dict[str, Any],
    repeat: int = 2,
    fail_safe_response: Any = "error",
    func_validate: Optional[Callable[..., bool]] = None,
    func_clean_up: Optional[Callable[..., Any]] = None,
    verbose: bool = False,
) -> Any:
    """Generate a response, retrying up to *repeat* times.

    Drop-in replacement for ``ollama_structure.safe_generate_response``.
    The *gpt_param* dict is accepted for backward-compatibility but the
    configured LLM provider (from env vars) is used for actual inference.
    """
    provider = _get_provider()
    for i in range(repeat):
        curr_response = provider.complete(prompt)
        if func_validate and func_validate(curr_response, prompt=prompt):
            if func_clean_up:
                return func_clean_up(curr_response, prompt=prompt)
            return curr_response
        if verbose:
            print(f"---- repeat count: {i}", curr_response)
    return fail_safe_response


def ChatGPT_safe_generate_response(
    prompt: str,
    example_output: Any,
    special_instruction: str,
    repeat: int = 3,
    fail_safe_response: Any = "error",
    func_validate: Optional[Callable[..., bool]] = None,
    func_clean_up: Optional[Callable[..., Any]] = None,
    verbose: bool = False,
) -> Any:
    """Generate a JSON-wrapped response with example output and instructions.

    Drop-in replacement for ``ollama_structure.ChatGPT_safe_generate_response``.
    """
    provider = _get_provider()
    full_prompt = '"""\n' + prompt + '\n"""\n'
    full_prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
    full_prompt += "Example output in json string format:\n"
    full_prompt += '{"output": "' + str(example_output) + '"}'

    if verbose:
        print("CHAT GPT PROMPT")
        print(full_prompt)

    for i in range(repeat):
        try:
            curr_response = provider.complete(full_prompt).strip()
            start_index = curr_response.rfind("{")
            end_index = curr_response.rfind("}") + 1
            curr_response = curr_response[start_index:end_index]
            curr_response = json.loads(curr_response)["output"]

            if func_validate and func_validate(curr_response, prompt=full_prompt):
                if func_clean_up:
                    return func_clean_up(curr_response, prompt=full_prompt)
                return curr_response

            if verbose:
                print(f"---- repeat count: {i}", curr_response)

        except Exception as e:
            print(f"[ERROR]: ChatGPT_safe_generate_response: {e}")

    return fail_safe_response


def ChatGPT_safe_generate_response_OLD(
    prompt: str,
    repeat: int = 3,
    fail_safe_response: Any = "error",
    func_validate: Optional[Callable[..., bool]] = None,
    func_clean_up: Optional[Callable[..., Any]] = None,
    verbose: bool = False,
) -> Any:
    """Older chat response variant without JSON wrapping.

    Drop-in replacement for ``ollama_structure.ChatGPT_safe_generate_response_OLD``.
    """
    provider = _get_provider()
    if verbose:
        print("CHAT GPT PROMPT")
        print(prompt)

    for i in range(repeat):
        try:
            curr_response = provider.complete(prompt).strip()
            if func_validate and func_validate(curr_response, prompt=prompt):
                if func_clean_up:
                    return func_clean_up(curr_response, prompt=prompt)
                return curr_response
            if verbose:
                print(f"---- repeat count: {i}")
                print(curr_response)
        except Exception:
            pass

    print("FAIL SAFE TRIGGERED")
    return fail_safe_response


def get_embedding(text: str, model: str = "") -> list[float]:
    """Return an embedding vector for *text* using the configured provider.

    Drop-in replacement for ``ollama_structure.get_embedding``.
    The *model* parameter is accepted for backward-compatibility but the
    embedding model configured via env vars (EMBEDDING_MODEL) is used.
    """
    text = text.replace("\n", " ")
    if not text:
        text = "this is blank"
    return _get_provider().embed(text)
