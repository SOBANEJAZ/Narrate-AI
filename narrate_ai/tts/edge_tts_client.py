"""Edge TTS implementation using Microsoft's Edge TTS service."""

import asyncio
from pathlib import Path

try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
except Exception:
    edge_tts = None
    EDGE_TTS_AVAILABLE = False


DEFAULT_EDGE_VOICE = "en-US-AriaNeural"


async def _synthesize_async(text, out_path, voice):
    """Async helper to synthesize with edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def synthesize_with_edge_tts(text, out_path, config):
    """Synthesize speech using Microsoft Edge TTS (free, no API key required)."""
    if not EDGE_TTS_AVAILABLE:
        return {
            "success": False,
            "audio_path": None,
            "error_message": "edge-tts package not installed. Run: pip install edge-tts",
        }

    voice = config.get("edge_tts_voice", DEFAULT_EDGE_VOICE)

    try:
        asyncio.run(_synthesize_async(text, out_path, voice))

        return {
            "success": True,
            "audio_path": out_path,
            "error_message": None,
        }

    except Exception as e:
        return {
            "success": False,
            "audio_path": None,
            "error_message": f"Edge TTS error: {e}",
        }


def get_available_voices():
    """Get list of available Edge TTS voices."""
    if not EDGE_TTS_AVAILABLE:
        return []

    voices = [
        {"name": "en-US-AriaNeural", "locale": "en-US", "gender": "Female"},
        {"name": "en-US-GuyNeural", "locale": "en-US", "gender": "Male"},
        {"name": "en-US-JennyNeural", "locale": "en-US", "gender": "Female"},
        {"name": "en-GB-SoniaNeural", "locale": "en-GB", "gender": "Female"},
        {"name": "en-GB-RyanNeural", "locale": "en-GB", "gender": "Male"},
        {"name": "en-AU-NatashaNeural", "locale": "en-AU", "gender": "Female"},
        {"name": "en-CA-ClaraNeural", "locale": "en-CA", "gender": "Female"},
    ]

    return voices
