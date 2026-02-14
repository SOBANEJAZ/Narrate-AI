"""Factory for creating TTS synthesizers."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from .base import SynthesisResult, TTSConfig
from .edge_tts_client import (
    get_available_voices as _get_edge_voices,
    synthesize_with_edge_tts,
)
from .elevenlabs import synthesize_with_elevenlabs


TTSProviderType = Literal["elevenlabs", "edge_tts"]


def create_tts_synthesizer(provider: TTSProviderType) -> callable:
    """Create a TTS synthesizer function for the given provider.

    Args:
        provider: TTS provider name ("elevenlabs" or "edge_tts")

    Returns:
        Synthesizer function with signature (text, out_path, config) -> SynthesisResult
    """
    if provider == "elevenlabs":
        return synthesize_with_elevenlabs
    elif provider == "edge_tts":
        return synthesize_with_edge_tts
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def get_available_voices(provider: TTSProviderType) -> list[dict[str, str]]:
    """Get available voices for a TTS provider.

    Args:
        provider: TTS provider name

    Returns:
        List of voice dictionaries
    """
    if provider == "edge_tts":
        return _get_edge_voices()
    elif provider == "elevenlabs":
        # ElevenLabs voices require API call; return common defaults
        return [
            {
                "name": "JBFqnCBsd6RMkjVDRZzb",
                "display": "Rachel (Default)",
                "locale": "en",
            },
            {"name": "pNInz6obpgDQGcFmaJgB", "display": "Adam", "locale": "en"},
            {"name": "onwK4e9ZLuTAKqWW03F9", "display": "Dorothy", "locale": "en"},
            {"name": "XB0fDUnXU5powFXDhCwa", "display": "Charlotte", "locale": "en"},
        ]
    else:
        return []
