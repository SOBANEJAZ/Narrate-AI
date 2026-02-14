"""Base types and interfaces for TTS providers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable, TypedDict

if TYPE_CHECKING:
    from ..config import PipelineConfig


class SynthesisResult(TypedDict):
    """Result of a TTS synthesis operation."""

    success: bool
    audio_path: Path | None
    error_message: str | None


class TTSConfig(TypedDict, total=False):
    """Configuration for TTS operations."""

    elevenlabs_api_key: str | None
    elevenlabs_voice_id: str
    elevenlabs_model_id: str
    edge_tts_voice: str
    request_timeout_seconds: int


TTSProvider = Callable[[str, Path, TTSConfig], SynthesisResult]


def create_tts_config(pipeline_config: PipelineConfig) -> TTSConfig:
    """Create TTS configuration from pipeline configuration.

    Args:
        pipeline_config: Pipeline configuration

    Returns:
        TTS configuration dictionary
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
