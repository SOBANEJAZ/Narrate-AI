"""LLM client module.

This module provides LLM operations as pure functions instead of a class.
"""

import json
import re
from typing import Type

from cerebras.cloud.sdk import Cerebras
from groq import Groq
from pydantic import BaseModel


class LLMError(RuntimeError):
    """Error raised for LLM-related failures."""

    pass


def create_llm_client(config):
    """Create an LLM client state dictionary."""
    return {
        "config": config,
        "_cerebras_client": None,
        "_groq_client": None,
    }


def _get_cerebras_client(client):
    """Get or create the Cerebras client (mutates state for caching)."""
    if client["_cerebras_client"] is None:
        if not client["config"]["cerebras_api_key"]:
            raise LLMError("Missing CEREBRAS_API_KEY")
        client["_cerebras_client"] = Cerebras(
            api_key=client["config"]["cerebras_api_key"]
        )
    return client["_cerebras_client"]


def _get_groq_client(client):
    """Get or create the Groq client (mutates state for caching)."""
    if client["_groq_client"] is None:
        if not client["config"]["groq_api_key"]:
            raise LLMError("Missing GROQ_API_KEY")
        client["_groq_client"] = Groq(api_key=client["config"]["groq_api_key"])
    return client["_groq_client"]


def _chat_completion(client, provider, prompt, temperature, max_tokens):
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


def generate_text(client, prompt, provider, temperature=0.4, max_tokens=1200):
    """Generate text using the specified LLM provider."""
    return _chat_completion(
        client,
        provider=provider,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def generate_json(client, prompt, provider, temperature=0.2, max_tokens=600):
    """Generate JSON using the specified LLM provider."""
    raw_text = _chat_completion(
        client,
        provider=provider,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return _extract_json(raw_text)


def _extract_json(text):
    """Extract JSON from text response."""
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise LLMError("LLM did not return JSON.")
    return json.loads(match.group(0))


def generate_pydantic(
    client,
    prompt,
    provider,
    model: Type[BaseModel],
    temperature: float = 0.2,
    max_tokens: int = 600,
):
    """Generate Pydantic model using the specified LLM provider.

    Uses JSON mode for better structure enforcement.
    """
    raw_text = _chat_completion(
        client,
        provider=provider,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    json_data = _extract_json(raw_text)
    return model.model_validate(json_data)
