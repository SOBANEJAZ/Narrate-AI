"""Text-to-speech module with multiple provider support."""

from typing import TYPE_CHECKING

from .base import TTSProvider, TTSConfig, SynthesisResult, create_tts_config
from .elevenlabs import synthesize_with_elevenlabs
from .edge_tts_client import synthesize_with_edge_tts
from .factory import create_tts_synthesizer, get_available_voices

if TYPE_CHECKING:
    from ..config import PipelineConfig

__all__ = [
    "TTSProvider",
    "TTSConfig",
    "SynthesisResult",
    "create_tts_config",
    "synthesize_with_elevenlabs",
    "synthesize_with_edge_tts",
    "create_tts_synthesizer",
    "get_available_voices",
]
