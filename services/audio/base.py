"""Base types and interfaces for TTS providers.

This module provides the configuration structure used by all TTS providers.
Each provider (ElevenLabs, Edge TTS) receives the same config format
but uses different fields.
"""

from typing import Any


def create_tts_config(pipeline_config):
    """Create TTS configuration from pipeline configuration.

    Extracts TTS-relevant settings from the pipeline config and
    provides sensible defaults for each provider.

    Args:
        pipeline_config: Full pipeline configuration dict

    Returns:
        TTS-specific config dict with provider settings
    """
    return {
        "elevenlabs_api_key": pipeline_config.get("elevenlabs_api_key"),
        "elevenlabs_voice_id": pipeline_config.get(
            "elevenlabs_voice_id", "JBFqnCBsd6RMkjVDRZzb"
        ),
        "elevenlabs_model_id": pipeline_config.get(
            "elevenlabs_model_id", "eleven_multilingual_v2"
        ),
        "edge_tts_voice": pipeline_config.get("edge_tts_voice", "en-US-AriaNeural"),
        "request_timeout_seconds": pipeline_config.get("request_timeout_seconds", 20),
    }
