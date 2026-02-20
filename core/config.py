"""Configuration module.

This module provides configuration as a dictionary with factory functions
instead of a dataclass. It also manages singleton Groq client caching.
"""

import os
from pathlib import Path

from groq import Groq


# Singleton Groq client cache
_groq_client_cache = None


def get_groq_client(api_key: str, model: str = None) -> Groq:
    """Get or create a Groq client (cached singleton).

    Args:
        api_key: Groq API key
        model: Optional model name (stored in client for reference)

    Returns:
        Groq client instance

    Raises:
        ValueError: If API key is missing
    """
    global _groq_client_cache

    if _groq_client_cache is None:
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")
        _groq_client_cache = Groq(api_key=api_key)

    return _groq_client_cache


def create_default_config():
    """Create a pipeline config with default values."""
    return {
        "run_root": Path("runs"),
        "max_websites": 4,
        "max_queries_per_segment": 5,
        "images_per_query": 5,
        "sentence_span_per_segment": 3,
        "resolution_width": 1280,
        "resolution_height": 720,
        "fps": 15,
        "transition_seconds": 0.3,
        "zoom_strength": 0.08,
        "background_mode": "black",
        "request_timeout_seconds": 20,
        "image_search_delay_seconds": 3,
        "cache_dir_name": "cache",
        "groq_api_key": None,
        "groq_model": "groq/mixtral-8x7b-32768",
        "elevenlabs_api_key": None,
        "elevenlabs_voice_id": "JBFqnCBsd6RMkjVDRZzb",
        "elevenlabs_model_id": "eleven_multilingual_v2",
        "edge_tts_voice": "en-US-AriaNeural",
        "tts_provider": "elevenlabs",
        "pinecone_api_key": None,
        "pinecone_environment": "us-east-1",
        "gemini_api_key": None,
    }


def create_config_from_env():
    """Create a pipeline config from environment variables."""
    config = create_default_config()
    config.update(
        {
            "groq_api_key": os.getenv("GROQ_API_KEY"),
            "groq_model": os.getenv("GROQ_MODEL", config["groq_model"]),
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY"),
            "elevenlabs_voice_id": os.getenv(
                "ELEVENLABS_VOICE_ID", config["elevenlabs_voice_id"]
            ),
            "elevenlabs_model_id": os.getenv(
                "ELEVENLABS_MODEL_ID", config["elevenlabs_model_id"]
            ),
            "edge_tts_voice": os.getenv("EDGE_TTS_VOICE", config["edge_tts_voice"]),
            "background_mode": os.getenv("BACKGROUND_MODE", config["background_mode"]),
            "tts_provider": os.getenv("TTS_PROVIDER", config["tts_provider"]),
            "pinecone_api_key": os.getenv("PINECONE_API"),
            "pinecone_environment": os.getenv(
                "PINECONE_ENV", config["pinecone_environment"]
            ),
            "gemini_api_key": os.getenv("GEMINI_API_KEY"),
        }
    )
    return config


def get_resolution(config):
    """Get the video resolution as a tuple."""
    return (config["resolution_width"], config["resolution_height"])


def update_config(config, **kwargs):
    """Create a new config with updated values (immutable update)."""
    new_config = dict(config)
    new_config.update(kwargs)
    return new_config
