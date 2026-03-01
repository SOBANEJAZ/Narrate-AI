"""LLM utilities module.

This module provides utilities for working with LLM responses.
Actual LLM client creation and Groq API calls are handled directly in agents.

Why this module exists:
- LLMs often return JSON wrapped in markdown fences or additional text
- We need to extract just the JSON part before parsing
- Pydantic validation ensures we get exactly the fields we expect
- Centralizes error handling for LLM-related failures
"""

import json
from typing import Type

from pydantic import BaseModel


class LLMError(RuntimeError):
    """Error raised when LLM response cannot be parsed or is invalid.

    This typically happens when:
    - LLM returns non-JSON text (e.g., an apology or clarification)
    - JSON is truncated or malformed
    - Required fields are missing from the response
    """

    pass


def extract_json(text: str) -> dict:
    """Extract JSON from text response using brace matching.

    LLMs often wrap JSON in markdown fences (```json ... ```) or add
    additional explanation text. This function handles both cases by:
    1. First trying to parse the entire text as JSON
    2. If that fails, finding the first { and matching } to extract JSON

    Args:
        text: Raw text response from LLM (may contain markdown, explanations)

    Returns:
        Parsed JSON as dictionary

    Raises:
        LLMError: If no valid JSON found in response
    """
    text = text.strip()

    # Fast path: if it's pure JSON, parse directly
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Slower path: find JSON object using brace matching
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

    Ensures the JSON has all required fields with correct types.
    If validation fails, Pydantic raises ValidationError with details.

    Args:
        json_data: Parsed JSON dictionary from LLM
        model: Pydantic model class to validate against

    Returns:
        Validated Pydantic model instance with proper types

    Raises:
        ValidationError: If JSON doesn't match the model schema
    """
    return model.model_validate(json_data)
