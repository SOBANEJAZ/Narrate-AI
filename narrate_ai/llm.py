"""LLM client module using functional programming style.

This module provides LLM operations as pure functions instead of a class,
following functional programming principles.
"""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from .config import PipelineConfig

try:
    from cerebras.cloud.sdk import Cerebras
except Exception:  # pragma: no cover - optional dependency fallback
    Cerebras = None  # type: ignore[assignment]

try:
    from groq import Groq
except Exception:  # pragma: no cover - optional dependency fallback
    Groq = None  # type: ignore[assignment]


class LLMError(RuntimeError):
    """Error raised for LLM-related failures."""

    pass


class LLMClientState(TypedDict):
    """State for LLM client operations."""

    config: PipelineConfig
    _cerebras_client: Any | None
    _groq_client: Any | None


def create_llm_client(config: PipelineConfig) -> LLMClientState:
    """Create an LLM client state dictionary.

    Args:
        config: Pipeline configuration

    Returns:
        Client state dictionary
    """
    return {
        "config": config,
        "_cerebras_client": None,
        "_groq_client": None,
    }


def _get_cerebras_client(client: LLMClientState) -> Any:
    """Get or create the Cerebras client (mutates state for caching)."""
    if client["_cerebras_client"] is None:
        if Cerebras is None:
            raise LLMError(
                "Cerebras SDK not installed. Run: pip install cerebras-cloud-sdk"
            )
        if not client["config"]["cerebras_api_key"]:
            raise LLMError("Missing CEREBRAS_API_KEY")
        client["_cerebras_client"] = Cerebras(
            api_key=client["config"]["cerebras_api_key"]
        )
    return client["_cerebras_client"]


def _get_groq_client(client: LLMClientState) -> Any:
    """Get or create the Groq client (mutates state for caching)."""
    if client["_groq_client"] is None:
        if Groq is None:
            raise LLMError("Groq SDK not installed. Run: pip install groq")
        if not client["config"]["groq_api_key"]:
            raise LLMError("Missing GROQ_API_KEY")
        client["_groq_client"] = Groq(api_key=client["config"]["groq_api_key"])
    return client["_groq_client"]


def _chat_completion(
    client: LLMClientState,
    *,
    provider: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Make a chat completion request to the specified provider."""
    messages = [
        {"role": "system", "content": "You are a documentary writing assistant."},
        {"role": "user", "content": prompt},
    ]

    if provider == "cerebras":
        cerebras_client = _get_cerebras_client(client)
        response = cerebras_client.chat.completions.create(
            messages=messages,
            model=client["config"]["cerebras_model"],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""

    elif provider == "groq":
        groq_client = _get_groq_client(client)
        response = groq_client.chat.completions.create(
            messages=messages,
            model=client["config"]["groq_model"],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""

    else:
        raise LLMError(f"Unsupported provider: {provider}")


def generate_text(
    client: LLMClientState,
    prompt: str,
    *,
    provider: str,
    fallback_text: str,
    temperature: float = 0.4,
    max_tokens: int = 1200,
) -> str:
    """Generate text using the specified LLM provider.

    Args:
        client: LLM client state
        prompt: The prompt to send
        provider: Provider name ("cerebras" or "groq")
        fallback_text: Text to return on error
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text or fallback on error
    """
    try:
        return _chat_completion(
            client,
            provider=provider,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        print(f"[LLM] Error generating text with {provider}: {e}")
        return fallback_text


def generate_json(
    client: LLMClientState,
    prompt: str,
    *,
    provider: str,
    fallback_json: dict[str, Any],
    temperature: float = 0.2,
    max_tokens: int = 600,
) -> dict[str, Any]:
    """Generate JSON using the specified LLM provider.

    Args:
        client: LLM client state
        prompt: The prompt to send
        provider: Provider name ("cerebras" or "groq")
        fallback_json: JSON to return on error
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Generated JSON or fallback on error
    """
    try:
        raw_text = _chat_completion(
            client,
            provider=provider,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return _extract_json(raw_text)
    except Exception as e:
        print(f"[LLM] Error generating JSON with {provider}: {e}")
        return fallback_json


def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from text response."""
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise LLMError("LLM did not return JSON.")
    return json.loads(match.group(0))
