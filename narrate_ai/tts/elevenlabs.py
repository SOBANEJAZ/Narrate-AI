"""ElevenLabs TTS implementation."""

import struct
import wave
from pathlib import Path

import requests


def synthesize_with_elevenlabs(text, out_path, config):
    """Synthesize speech using ElevenLabs API."""
    api_key = config.get("elevenlabs_api_key")
    if not api_key:
        raise ValueError("ElevenLabs API key not configured")

    voice_id = config.get("elevenlabs_voice_id")
    model_id = config.get("elevenlabs_model_id")
    timeout = config.get("request_timeout_seconds", 20)

    endpoint = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    response = requests.post(
        endpoint,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/wav",
        },
        json={
            "text": text,
            "model_id": model_id,
            "output_format": "pcm_44100",
        },
        timeout=timeout,
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        raise RuntimeError("ElevenLabs API returned JSON instead of audio")

    audio_content = response.content
    if audio_content.startswith(b"RIFF") or audio_content.startswith(b"ID3"):
        print(
            f"[TTS] ElevenLabs returned containerized audio ({len(audio_content)} bytes), saving directly."
        )
        out_path.write_bytes(audio_content)
    else:
        print(f"[TTS] ElevenLabs returned raw PCM, wrapping in WAV container.")
        _write_pcm_as_wav(out_path, audio_content, sample_rate=44100)

    return {
        "success": True,
        "audio_path": out_path,
        "error_message": None,
    }


def _write_pcm_as_wav(out_path, pcm_bytes, sample_rate):
    """Write PCM bytes as a WAV file."""
    with wave.open(str(out_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
