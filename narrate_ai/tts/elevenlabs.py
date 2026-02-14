"""ElevenLabs TTS implementation."""

import struct
import wave
from pathlib import Path

import requests


def synthesize_with_elevenlabs(text, out_path, config):
    """Synthesize speech using ElevenLabs API."""
    api_key = config.get("elevenlabs_api_key")
    if not api_key:
        return {
            "success": False,
            "audio_path": None,
            "error_message": "ElevenLabs API key not configured",
        }

    voice_id = config.get("elevenlabs_voice_id", "JBFqnCBsd6RMkjVDRZzb")
    model_id = config.get("elevenlabs_model_id", "eleven_multilingual_v2")
    timeout = config.get("request_timeout_seconds", 20)

    endpoint = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    try:
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
            return {
                "success": False,
                "audio_path": None,
                "error_message": "API returned JSON instead of audio",
            }

        _write_pcm_as_wav(out_path, response.content, sample_rate=44100)

        return {
            "success": True,
            "audio_path": out_path,
            "error_message": None,
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "audio_path": None,
            "error_message": f"ElevenLabs API error: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "audio_path": None,
            "error_message": f"Unexpected error: {e}",
        }


def _write_pcm_as_wav(out_path, pcm_bytes, sample_rate):
    """Write PCM bytes as a WAV file."""
    with wave.open(str(out_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
