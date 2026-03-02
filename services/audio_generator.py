"""Audio Generator Service - TTS and narration synthesis.

Consolidated module providing:
- ElevenLabs TTS provider
- Microsoft Edge TTS provider
- TTS synthesizer factory
- High-level narration orchestration
"""

import asyncio
import wave
from pathlib import Path

import edge_tts
from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError


DEFAULT_EDGE_VOICE = "en-US-AriaNeural"

OUTPUT_FORMAT_PRIMARY = "wav_44100"
OUTPUT_FORMAT_FALLBACK = "mp3_44100_128"


async def _synthesize_edge_async(text, out_path, voice):
    """Async helper to synthesize with edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def synthesize_with_edge_tts(text, out_path, config):
    """Synthesize speech using Microsoft Edge TTS.

    This is a free alternative to ElevenLabs. Quality is lower
    but no API key is required.

    Args:
        text: Text to synthesize
        out_path: Output file path
        config: TTS config with voice setting

    Returns:
        Dict with success status, audio path, and error message
    """
    voice = config.get("edge_tts_voice", DEFAULT_EDGE_VOICE)

    asyncio.run(_synthesize_edge_async(text, out_path, voice))

    return {
        "success": True,
        "audio_path": out_path,
        "error_message": None,
    }


def get_available_edge_voices():
    """Get list of available Edge TTS voices.

    Returns:
        List of voice dicts with name, locale, and gender
    """
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


def _write_raw_as_wav(out_path, audio_bytes, sample_rate):
    """Write raw audio bytes as a WAV file.

    Args:
        out_path: Output file path
        audio_bytes: Raw audio data
        sample_rate: Sample rate in Hz
    """
    with wave.open(str(out_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)


def synthesize_with_elevenlabs(text, out_path, config):
    """Synthesize speech using ElevenLabs API.

    Args:
        text: Text to synthesize
        out_path: Output file path (.wav)
        config: TTS config with API key and voice settings

    Returns:
        Dict with success status, audio path, and error message
    """
    api_key = config.get("elevenlabs_api_key")
    if not api_key:
        raise ValueError("ElevenLabs API key not configured")

    voice_id = config.get("elevenlabs_voice_id")
    model_id = config.get("elevenlabs_model_id", "eleven_multilingual_v2")

    client = ElevenLabs(api_key=api_key)

    output_format = OUTPUT_FORMAT_PRIMARY
    audio_stream = None
    error_message = None

    try:
        audio_stream = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format=output_format,
        )
        audio_bytes = b"".join(chunk for chunk in audio_stream)
    except ApiError as e:
        error_str = str(e)
        error_message_raw = ""

        if isinstance(e.body, dict):
            error_detail = e.body.get("detail", {})
            if isinstance(error_detail, dict):
                error_code = error_detail.get("code", "")
                error_message_raw = error_detail.get("message", "")
            else:
                error_code = ""
                error_message_raw = str(error_detail)
        else:
            error_code = ""
            error_message_raw = ""

        if "wav_44100" in error_str or "output_format" in error_str.lower():
            print(
                f"[TTS] ElevenLabs wav_44100 not available on current subscription. "
                f"Falling back to {OUTPUT_FORMAT_FALLBACK}",
                flush=True,
            )
            output_format = OUTPUT_FORMAT_FALLBACK

            try:
                audio_stream = client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id=model_id,
                    output_format=output_format,
                )
                audio_bytes = b"".join(chunk for chunk in audio_stream)
            except ApiError as e2:
                error_message = f"ElevenLabs API error after fallback: {e2}"
                print(f"[TTS] ERROR: {error_message}", flush=True)
                return {
                    "success": False,
                    "audio_path": None,
                    "error_message": error_message,
                }
        else:
            error_message = f"ElevenLabs API error: {e}"
            print(f"[TTS] ERROR: {error_message}", flush=True)
            return {
                "success": False,
                "audio_path": None,
                "error_message": error_message,
            }

    if output_format.startswith("mp3"):
        print(
            f"[TTS] ElevenLabs returned MP3 audio ({len(audio_bytes)} bytes), saving as MP3."
        )
        out_path = out_path.with_suffix(".mp3")
        out_path.write_bytes(audio_bytes)
    elif audio_bytes.startswith(b"RIFF"):
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


def create_tts_synthesizer(provider):
    """Create a TTS synthesizer function for the given provider.

    Factory function that returns the appropriate synthesizer
    based on the provider name.

    Args:
        provider: Provider name ("elevenlabs" or "edge_tts")

    Returns:
        Synthesize function for the provider

    Raises:
        ValueError: If provider is unknown
    """
    if provider == "elevenlabs":
        return synthesize_with_elevenlabs
    elif provider == "edge_tts":
        return synthesize_with_edge_tts
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def get_available_voices(provider):
    """Get available voices for a TTS provider.

    Args:
        provider: Provider name

    Returns:
        List of voice dicts with name, display, locale
    """
    if provider == "edge_tts":
        return get_available_edge_voices()
    elif provider == "elevenlabs":
        return [
            {
                "name": "JBFqnCBsd6RMkjVDRZzb",
                "display": "Rachel (Default)",
                "locale": "en",
            },
            {"name": "pNInz6obpgDQGcFmaJgB", "display": "Adam", "locale": "en"},
            {"name": "onwK4e9ZLuTAKqWW03F9", "display": "Dorothy", "locale": "en"},
            {"name": "XB0fDUnXU5powFXDhCwa", "display": "Charlotte", "locale": "en"},
        ]
    else:
        return []


def synthesize_audio(config, segments, audio_root, provider="elevenlabs"):
    """Synthesize audio narration for all script segments.

    Uses the configured TTS provider (ElevenLabs or Edge TTS) to
    generate WAV audio files for each segment's text.

    Args:
        config: Pipeline configuration
        segments: List of segment dicts with text
        audio_root: Directory to save audio files
        provider: TTS provider name ("elevenlabs" or "edge_tts")

    Returns:
        Segments with narration_audio_path added

    Raises:
        RuntimeError: If TTS synthesis fails for any segment
    """
    print(
        f"[TTS] Generating narration for {len(segments)} segments (provider={provider})",
        flush=True,
    )
    audio_root.mkdir(parents=True, exist_ok=True)

    synthesizer = create_tts_synthesizer(provider)

    for segment in segments:
        out_path = audio_root / f"segment_{segment['segment_id']:03d}.wav"
        result = synthesizer(segment["text"], out_path, config)

        if not result["success"]:
            if provider == "elevenlabs":
                print(
                    f"[TTS] ElevenLabs failed, falling back to edge_tts",
                    flush=True,
                )
                provider = "edge_tts"
                synthesizer = create_tts_synthesizer(provider)
                out_path = audio_root / f"segment_{segment['segment_id']:03d}.wav"
                result = synthesizer(segment["text"], out_path, config)

                if not result["success"]:
                    raise RuntimeError(
                        f"TTS failed for segment {segment['segment_id']}: {result.get('error_message', 'unknown error')}"
                    )

        print(
            f"[TTS] Segment {segment['segment_id']}: {provider} audio generated",
            flush=True,
        )

        segment["narration_audio_path"] = out_path

    return segments
