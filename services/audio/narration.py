"""Narration Service - Audio synthesis for script segments.

This module orchestrates TTS synthesis for all script segments.
It:
1. Creates the appropriate TTS synthesizer based on provider
2. Generates audio for each segment
3. Stores audio file paths in segment dicts

The synthesized audio is later used for timeline building and
video assembly.
"""

from pathlib import Path

from services.audio import create_tts_config, create_tts_synthesizer


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
    tts_config = create_tts_config(config)

    for segment in segments:
        out_path = audio_root / f"segment_{segment['segment_id']:03d}.wav"
        result = synthesizer(segment["text"], out_path, tts_config)

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
