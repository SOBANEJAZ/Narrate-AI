"""Edge TTS implementation using Microsoft's Edge TTS service."""

import asyncio
from pathlib import Path

import edge_tts


DEFAULT_EDGE_VOICE = "en-US-AriaNeural"


async def _synthesize_async(text, out_path, voice):
    """Async helper to synthesize with edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def synthesize_with_edge_tts(text, out_path, config):
    """Synthesize speech using Microsoft Edge TTS (free, no API key required)."""
    voice = config.get("edge_tts_voice", DEFAULT_EDGE_VOICE)

    asyncio.run(_synthesize_async(text, out_path, voice))

    return {
        "success": True,
        "audio_path": out_path,
        "error_message": None,
    }


def get_available_voices():
    """Get list of available Edge TTS voices."""
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
