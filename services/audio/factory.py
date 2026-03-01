"""TTS Synthesizer Factory.

Provides a unified interface for creating TTS synthesizers.
Supports multiple providers while maintaining consistent API.
"""

from .edge_tts_client import (
    get_available_voices as _get_edge_voices,
    synthesize_with_edge_tts,
)
from .elevenlabs import synthesize_with_elevenlabs


def create_tts_synthesizer(provider):
    """Create a TTS synthesizer function for the given provider.

    Factory function that returns the appropriate synthesizer
    based on the provider name.

    Args:
        provider: Provider name ("elevenlabs" or "edge_tts")

    Returns:
        Synthesize function for the provider

    Raises:
        ValueError: If provider is unknown
    """
    if provider == "elevenlabs":
        return synthesize_with_elevenlabs
    elif provider == "edge_tts":
        return synthesize_with_edge_tts
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def get_available_voices(provider):
    """Get available voices for a TTS provider.

    Args:
        provider: Provider name

    Returns:
        List of voice dicts with name, display, locale
    """
    if provider == "edge_tts":
        return _get_edge_voices()
    elif provider == "elevenlabs":
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
