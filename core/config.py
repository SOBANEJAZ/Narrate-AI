"""Configuration module.

This module provides configuration as a dictionary with factory functions
instead of a dataclass.

Configuration Flow:
1. create_default_config() - Sets all sensible defaults
2. create_config_from_env() - Overrides with environment variables

Environment Variables:
- GROQ_API_KEY: LLM API key (required for agents)
- SERPER_API_KEY: Web search API key
- ELEVENLABS_API_KEY: Premium TTS (optional, edge_tts is free alternative)
- PINECONE_API: Vector database API (optional)
- BACKGROUND_MODE: "black" or "blur"
- TTS_PROVIDER: "elevenlabs" or "edge_tts"
"""

import os
from pathlib import Path

from dotenv import load_dotenv


def create_default_config():
    """Create a pipeline config with all default values.

    These defaults produce a 1280x720 video at 15fps with black letterboxing.
    Agents use Groq LLM, images are searched via Serper.dev, and ElevenLabs
    is the default TTS provider (falls back to edge_tts if no API key).

    Returns:
        Dict with all configuration keys and their default values
    """
    return {
        "run_root": Path("runs"),
        "max_websites": 4,
        "max_queries_per_segment": 3,
        "sentence_span_per_segment": 3,
        "resolution_width": 1280,
        "resolution_height": 720,
        "fps": 15,
        "transition_seconds": 0.3,
        "zoom_strength": 0.015,
        "request_timeout_seconds": 20,
        "image_search_delay_seconds": 3,
        "cache_dir_name": "cache",
        "edge_tts_voice": "en-US-AriaNeural",
        "tts_provider": "elevenlabs",
        "pinecone_api_key": None,
        "pinecone_environment": "us-east-1",
        "top_k": 1,
    }


def create_config_from_env():
    """Create a pipeline config from environment variables.

    Loads .env file first, then reads environment variables to override defaults.
    Missing environment variables keep their default values.

    Returns:
        Dict with defaults overridden by environment variables
    """
    load_dotenv()
    config = create_default_config()
    config.update(
        {
            "groq_api_key": os.getenv("GROQ_API_KEY"),
            "serper_api_key": os.getenv("SERPER_API_KEY"),
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY"),
            "elevenlabs_voice_id": os.getenv("ELEVENLABS_VOICE_ID"),
            "elevenlabs_model_id": os.getenv("ELEVENLABS_MODEL_ID"),
            "edge_tts_voice": os.getenv("EDGE_TTS_VOICE", config["edge_tts_voice"]),
            "tts_provider": os.getenv("TTS_PROVIDER", config["tts_provider"]),
            "pinecone_api_key": os.getenv("PINECONE_API"),
            "pinecone_environment": os.getenv(
                "PINECONE_ENV", config["pinecone_environment"]
            ),
            "top_k": int(os.getenv("TOP_K", config["top_k"])),
        }
    )
    return config
