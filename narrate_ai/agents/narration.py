"""Narration agent using functional programming style with multiple TTS providers."""

import math
import struct
import wave
from pathlib import Path

from ..tts import create_tts_config, create_tts_synthesizer


def synthesize_audio(config, segments, audio_root, provider="elevenlabs"):
    """Synthesize audio for script segments."""
    print(
        f"[TTS] Generating narration for {len(segments)} segments (provider={provider})",
        flush=True,
    )
    audio_root.mkdir(parents=True, exist_ok=True)

    synthesizer = create_tts_synthesizer(provider)
    tts_config = create_tts_config(config)

    for segment in segments:
        out_path = audio_root / f"segment_{segment['segment_id']:03d}.wav"
        result = synthesizer(segment["text"], out_path, tts_config)

        if result["success"]:
            print(
                f"[TTS] Segment {segment['segment_id']}: {provider} audio generated",
                flush=True,
            )
        else:
            duration = _estimate_duration(segment["text"])
            _write_fallback_audio(out_path, duration)
            print(
                f"[TTS] Segment {segment['segment_id']}: {provider} failed ({result.get('error_message', 'unknown error')}), used fallback audio",
                flush=True,
            )

        segment["narration_audio_path"] = out_path

    return segments


def _estimate_duration(text, words_per_minute=150):
    """Estimate audio duration based on word count."""
    words = max(1, len(text.split()))
    duration = (words / words_per_minute) * 60.0
    return max(3.0, duration)


def _write_fallback_audio(out_path, duration_seconds):
    """Generate fallback sine wave audio."""
    sample_rate = 22050
    amplitude = 0.1
    frequency = 210.0
    sample_count = int(sample_rate * duration_seconds)

    with wave.open(str(out_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for index in range(sample_count):
            envelope = 0.25 if index % sample_rate < 2500 else 0.08
            value = (
                amplitude
                * envelope
                * math.sin((2.0 * math.pi * frequency * index) / sample_rate)
            )
            frames.extend(struct.pack("<h", int(32767.0 * value)))
        wav_file.writeframes(bytes(frames))
