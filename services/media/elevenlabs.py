"""ElevenLabs TTS implementation."""

import wave
from pathlib import Path

from elevenlabs.client import ElevenLabs


def synthesize_with_elevenlabs(text, out_path, config):
    """Synthesize speech using ElevenLabs API."""
    api_key = config.get("elevenlabs_api_key")
    if not api_key:
        raise ValueError("ElevenLabs API key not configured")

    voice_id = config.get("elevenlabs_voice_id")
    model_id = config.get("elevenlabs_model_id", "eleven_multilingual_v2")

    client = ElevenLabs(api_key=api_key)

    audio_stream = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="wav_44100",
    )

    audio_bytes = b"".join(chunk for chunk in audio_stream)

    if audio_bytes.startswith(b"RIFF"):
        print(
            f"[TTS] ElevenLabs returned WAV audio ({len(audio_bytes)} bytes), saving directly."
        )
        out_path.write_bytes(audio_bytes)
    else:
        print(f"[TTS] ElevenLabs returned raw audio, wrapping in WAV container.")
        _write_raw_as_wav(out_path, audio_bytes, sample_rate=44100)

    return {
        "success": True,
        "audio_path": out_path,
        "error_message": None,
    }


def _write_raw_as_wav(out_path, audio_bytes, sample_rate):
    """Write raw audio bytes as a WAV file."""
    with wave.open(str(out_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)
