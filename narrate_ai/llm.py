from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import requests

from .config import PipelineConfig


class LLMError(RuntimeError):
    pass


@dataclass(slots=True)
class LLMClient:
    config: PipelineConfig

    def generate_text(
        self,
        prompt: str,
        *,
        provider: str,
        fallback_text: str,
        temperature: float = 0.4,
        max_tokens: int = 1200,
    ) -> str:
        try:
            return self._chat_completion(
                provider=provider,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception:
            return fallback_text

    def generate_json(
        self,
        prompt: str,
        *,
        provider: str,
        fallback_json: dict[str, Any],
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> dict[str, Any]:
        try:
            raw_text = self._chat_completion(
                provider=provider,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return self._extract_json(raw_text)
        except Exception:
            return fallback_json

    def _chat_completion(
        self,
        *,
        provider: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if provider == "groq":
            api_key = self.config.groq_api_key
            model = self.config.groq_model
            base_url = "https://api.groq.com/openai/v1/chat/completions"
        elif provider == "cerebras":
            api_key = self.config.cerebras_api_key
            model = self.config.cerebras_model
            base_url = "https://api.cerebras.ai/v1/chat/completions"
        else:
            raise LLMError(f"Unsupported provider: {provider}")

        if not api_key:
            raise LLMError(f"Missing API key for provider: {provider}")

        response = requests.post(
            base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a documentary writing assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=self.config.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices", [])
        if not choices:
            raise LLMError("No response choices returned from LLM API.")
        return str(choices[0]["message"]["content"]).strip()

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            return json.loads(text)

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise LLMError("LLM did not return JSON.")
        return json.loads(match.group(0))
