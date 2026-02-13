from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PipelineConfig:
    run_root: Path = Path("runs")
    max_websites: int = 4
    max_queries_per_segment: int = 5
    images_per_query: int = 5
    sentence_span_per_segment: int = 3
    resolution_width: int = 1280
    resolution_height: int = 720
    fps: int = 24
    transition_seconds: float = 0.3
    zoom_strength: float = 0.04
    background_mode: str = "black"  # `black` or `blur`
    request_timeout_seconds: int = 20
    cache_dir_name: str = "cache"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    cerebras_api_key: str | None = None
    cerebras_model: str = "llama-3.1-70b"
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    @property
    def resolution(self) -> tuple[int, int]:
        return (self.resolution_width, self.resolution_height)

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        return cls(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            cerebras_api_key=os.getenv("CEREBRAS_API_KEY"),
            cerebras_model=os.getenv("CEREBRAS_MODEL", "llama-3.1-70b"),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),
            elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
            background_mode=os.getenv("BACKGROUND_MODE", "black"),
        )
