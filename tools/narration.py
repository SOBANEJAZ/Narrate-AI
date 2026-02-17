"""Narration agent with multiple TTS providers."""

from pathlib import Path

from tools.tts import create_tts_config, create_tts_synthesizer


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
