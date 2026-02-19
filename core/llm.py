"""LLM client module.

This module provides LLM operations using Groq SDK exclusively.
"""

import json
from typing import Type

from groq import Groq
from pydantic import BaseModel


class LLMError(RuntimeError):
    """Error raised for LLM-related failures."""

    pass


def create_llm_client(config):
    """Create an LLM client state dictionary."""
    return {
        "config": config,
        "_groq_client": None,
    }


def _get_groq_client(client):
    """Get or create the Groq client (mutates state for caching)."""
    if client["_groq_client"] is None:
        if not client["config"]["groq_api_key"]:
            raise LLMError("Missing GROQ_API_KEY")
        client["_groq_client"] = Groq(api_key=client["config"]["groq_api_key"])
    return client["_groq_client"]


def _chat_completion(client, prompt, temperature, model=None):
    """Make a chat completion request to Groq."""
    messages = [
        {"role": "system", "content": "You are a documentary writing assistant."},
        {"role": "user", "content": prompt},
    ]

    groq_client = _get_groq_client(client)
    response = groq_client.chat.completions.create(
        messages=messages,
        model=model or client["config"]["groq_model"],
        temperature=temperature,
    )
    content = response.choices[0].message.content
    return content if content is not None else ""


def generate_text(client, prompt, temperature=0.4, model=None):
    """Generate text using Groq."""
    return _chat_completion(
        client,
        prompt=prompt,
        temperature=temperature,
        model=model,
    )


def generate_json(client, prompt, temperature=0.2):
    """Generate JSON using Groq."""
    raw_text = _chat_completion(
        client,
        prompt=prompt,
        temperature=temperature,
    )
    return _extract_json(raw_text)


def _extract_json(text):
    """Extract JSON from text response using brace matching."""
    text = text.strip()

    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    if start == -1:
        raise LLMError("LLM did not return JSON.")

    depth = 0
    for i, char in enumerate(text[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                json_str = text[start : i + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    raise LLMError(f"Invalid JSON: {json_str[:100]}...")

    raise LLMError("LLM did not return valid JSON.")


def generate_pydantic(
    client,
    prompt,
    model: Type[BaseModel],
    temperature: float = 0.2,
    model_override: str | None = None,
):
    """Generate Pydantic model using Groq.

    Uses JSON mode for better structure enforcement.
    """
    raw_text = _chat_completion(
        client,
        prompt=prompt,
        temperature=temperature,
        model=model_override,
    )
    json_data = _extract_json(raw_text)
    return model.model_validate(json_data)
