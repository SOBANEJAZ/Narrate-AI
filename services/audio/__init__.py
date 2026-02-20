"""Audio service: TTS and narration synthesis."""

from .base import create_tts_config
from .edge_tts_client import synthesize_with_edge_tts
from .elevenlabs import synthesize_with_elevenlabs
from .factory import create_tts_synthesizer, get_available_voices
from .narration import synthesize_audio

__all__ = [
    "create_tts_config",
    "synthesize_with_elevenlabs",
    "synthesize_with_edge_tts",
    "create_tts_synthesizer",
    "get_available_voices",
    "synthesize_audio",
]
