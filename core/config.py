"""Configuration module.

This module provides configuration as a dictionary with factory functions
instead of a dataclass. It also manages singleton Groq client caching.

Configuration Flow:
1. create_default_config() - Sets all sensible defaults
2. create_config_from_env() - Overrides with environment variables
3. update_config() - Applies CLI/UI overrides (immutable update)

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

from groq import Groq


# Singleton Groq client cache - avoids recreating client for each request
_groq_client_cache = None


def _load_dotenv_if_present(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE pairs from .env if file exists.

    This is a minimal .env loader that only handles KEY=VALUE format.
    Skips comments (#), empty lines, and already-set environment variables.

    Args:
        path: Path to .env file (defaults to ".env" in project root)
    """
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if not key or key in os.environ:
            continue
        os.environ[key] = value


def get_groq_client(api_key: str, model: str = None) -> Groq:
    """Get or create a Groq client (cached singleton).

    Uses a global singleton to avoid creating multiple Groq client instances.
    This is safe because the Groq client is stateless after initialization.

    Args:
        api_key: Groq API key (from config["groq_api_key"])
        model: Optional model name (stored in client for reference, not used)

    Returns:
        Groq client instance - singleton, shared across all agents

    Raises:
        ValueError: If API key is missing/empty
    """
    global _groq_client_cache

    if _groq_client_cache is None:
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")
        _groq_client_cache = Groq(api_key=api_key)

    return _groq_client_cache


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
    _load_dotenv_if_present()
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


def get_resolution(config):
    """Get the video resolution as a tuple (width, height).

    Args:
        config: Pipeline configuration dict

    Returns:
        Tuple of (width, height) in pixels
    """
    return (config["resolution_width"], config["resolution_height"])


def get_top_k(config):
    """Get the top_k value for RAG retrieval.

    This determines how many relevant text chunks are retrieved from
    the vector database for each search query.

    Args:
        config: Pipeline configuration dict

    Returns:
        Integer number of results to retrieve (default 1)
    """
    return config.get("top_k", 1)


def update_config(config, **kwargs):
    """Create a new config with updated values (immutable update).

    Creates a copy of the config and applies updates, leaving the
    original unchanged. This is useful for CLI overrides.

    Args:
        config: Original configuration dict
        **kwargs: Keys and values to update

    Returns:
        New config dict with updates applied
    """
    new_config = dict(config)
    new_config.update(kwargs)
    return new_config
