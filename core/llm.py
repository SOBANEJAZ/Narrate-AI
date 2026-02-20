"""LLM utilities module.

This module provides utilities for working with LLM responses.
Actual LLM client creation and Groq API calls are handled directly in agents.
"""

import json
from typing import Type

from pydantic import BaseModel


class LLMError(RuntimeError):
    """Error raised for LLM-related failures."""

    pass


def extract_json(text: str) -> dict:
    """Extract JSON from text response using brace matching.

    Attempts to parse JSON from LLM output, handling cases where JSON
    is embedded in additional text.

    Args:
        text: Raw text response from LLM

    Returns:
        Parsed JSON as dictionary

    Raises:
        LLMError: If no valid JSON found in response
    """
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


def validate_pydantic(
    json_data: dict,
    model: Type[BaseModel],
) -> BaseModel:
    """Validate JSON data against a Pydantic model.

    Args:
        json_data: Parsed JSON dictionary
        model: Pydantic model class to validate against

    Returns:
        Validated Pydantic model instance
    """
    return model.model_validate(json_data)
