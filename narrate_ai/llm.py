from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

try:
    from cerebras.cloud.sdk import Cerebras
except Exception:  # pragma: no cover - optional dependency fallback
    Cerebras = None  # type: ignore[assignment]

try:
    from groq import Groq
except Exception:  # pragma: no cover - optional dependency fallback
    Groq = None  # type: ignore[assignment]

from .config import PipelineConfig


class LLMError(RuntimeError):
    pass


@dataclass
class LLMClient:
    config: PipelineConfig

    def __post_init__(self):
        self._cerebras_client = None
        self._groq_client = None

    def _get_cerebras_client(self):
        if self._cerebras_client is None:
            if Cerebras is None:
                raise LLMError(
                    "Cerebras SDK not installed. Run: pip install cerebras-cloud-sdk"
                )
            if not self.config.cerebras_api_key:
                raise LLMError("Missing CEREBRAS_API_KEY")
            self._cerebras_client = Cerebras(api_key=self.config.cerebras_api_key)
        return self._cerebras_client

    def _get_groq_client(self):
        if self._groq_client is None:
            if Groq is None:
                raise LLMError("Groq SDK not installed. Run: pip install groq")
            if not self.config.groq_api_key:
                raise LLMError("Missing GROQ_API_KEY")
            self._groq_client = Groq(api_key=self.config.groq_api_key)
        return self._groq_client

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
        except Exception as e:
            print(f"[LLM] Error generating text with {provider}: {e}")
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
        except Exception as e:
            print(f"[LLM] Error generating JSON with {provider}: {e}")
            return fallback_json

    def _chat_completion(
        self,
        *,
        provider: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        messages = [
            {"role": "system", "content": "You are a documentary writing assistant."},
            {"role": "user", "content": prompt},
        ]

        if provider == "cerebras":
            client = self._get_cerebras_client()
            response = client.chat.completions.create(
                messages=messages,
                model=self.config.cerebras_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        elif provider == "groq":
            client = self._get_groq_client()
            response = client.chat.completions.create(
                messages=messages,
                model=self.config.groq_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        else:
            raise LLMError(f"Unsupported provider: {provider}")

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            return json.loads(text)

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise LLMError("LLM did not return JSON.")
        return json.loads(match.group(0))
