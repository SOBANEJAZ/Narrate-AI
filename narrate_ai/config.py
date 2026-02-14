"""Configuration module using functional programming style.

This module provides configuration as a dictionary with factory functions
instead of a dataclass, following functional programming principles.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

from .tts.factory import TTSProviderType


class PipelineConfig(TypedDict):
    """Pipeline configuration using TypedDict for functional style."""

    run_root: Path
    max_websites: int
    max_queries_per_segment: int
    images_per_query: int
    sentence_span_per_segment: int
    resolution_width: int
    resolution_height: int
    fps: int
    transition_seconds: float
    zoom_strength: float
    background_mode: str
    request_timeout_seconds: int
    cache_dir_name: str
    groq_api_key: str | None
    groq_model: str
    cerebras_api_key: str | None
    cerebras_model: str
    elevenlabs_api_key: str | None
    elevenlabs_voice_id: str
    elevenlabs_model_id: str
    edge_tts_voice: str
    tts_provider: TTSProviderType


def create_default_config() -> PipelineConfig:
    """Create a pipeline config with default values."""
    return {
        "run_root": Path("runs"),
        "max_websites": 4,
        "max_queries_per_segment": 5,
        "images_per_query": 5,
        "sentence_span_per_segment": 3,
        "resolution_width": 1280,
        "resolution_height": 720,
        "fps": 24,
        "transition_seconds": 0.3,
        "zoom_strength": 0.04,
        "background_mode": "black",
        "request_timeout_seconds": 20,
        "cache_dir_name": "cache",
        "groq_api_key": None,
        "groq_model": "openai/gpt-oss-120b",
        "cerebras_api_key": None,
        "cerebras_model": "gpt-oss-120b",
        "elevenlabs_api_key": None,
        "elevenlabs_voice_id": "JBFqnCBsd6RMkjVDRZzb",
        "elevenlabs_model_id": "eleven_multilingual_v2",
        "edge_tts_voice": "en-US-AriaNeural",
        "tts_provider": "elevenlabs",
    }


def create_config_from_env() -> PipelineConfig:
    """Create a pipeline config from environment variables."""
    config = create_default_config()
    config.update(
        {
            "groq_api_key": os.getenv("GROQ_API_KEY"),
            "groq_model": os.getenv("GROQ_MODEL", config["groq_model"]),
            "cerebras_api_key": os.getenv("CEREBRAS_API_KEY"),
            "cerebras_model": os.getenv("CEREBRAS_MODEL", config["cerebras_model"]),
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
        }
    )
    return config


def get_resolution(config: PipelineConfig) -> tuple[int, int]:
    """Get the video resolution as a tuple."""
    return (config["resolution_width"], config["resolution_height"])


def update_config(
    config: PipelineConfig,
    **kwargs: object,
) -> PipelineConfig:
    """Create a new config with updated values (immutable update)."""
    new_config = dict(config)
    new_config.update(kwargs)
    return new_config  # type: ignore[return-value]
