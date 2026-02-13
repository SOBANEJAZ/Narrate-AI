from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

import requests

from ..config import PipelineConfig
from ..models import ScriptSegment


@dataclass(slots=True)
class NarrationAgent:
    config: PipelineConfig
    words_per_minute: int = 150

    def synthesize(self, segments: list[ScriptSegment], audio_root: Path) -> list[ScriptSegment]:
        print(
            f"[TTS] Generating narration for {len(segments)} segments (ElevenLabs voice={self.config.elevenlabs_voice_id})",
            flush=True,
        )
        audio_root.mkdir(parents=True, exist_ok=True)
        for segment in segments:
            out_path = audio_root / f"segment_{segment.segment_id:03d}.wav"
            success = self._synthesize_with_elevenlabs(segment.text, out_path)
            if not success:
                duration = self._estimate_duration(segment.text)
                self._write_fallback_audio(out_path, duration)
                print(
                    f"[TTS] Segment {segment.segment_id}: ElevenLabs failed/unset, used local fallback audio",
                    flush=True,
                )
            else:
                print(
                    f"[TTS] Segment {segment.segment_id}: ElevenLabs audio generated",
                    flush=True,
                )
            segment.narration_audio_path = out_path
        return segments

    def _synthesize_with_elevenlabs(self, text: str, out_path: Path) -> bool:
        if not self.config.elevenlabs_api_key:
            return False

        endpoint = (
            "https://api.elevenlabs.io/v1/text-to-speech/"
            f"{self.config.elevenlabs_voice_id}"
        )
        try:
            response = requests.post(
                endpoint,
                headers={
                    "xi-api-key": self.config.elevenlabs_api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/wav",
                },
                json={
                    "text": text,
                    "model_id": self.config.elevenlabs_model_id,
                    "output_format": "pcm_44100",
                },
                timeout=self.config.request_timeout_seconds,
            )
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return False

            self._write_pcm_as_wav(out_path, response.content, sample_rate=44100)
            return True
        except Exception:
            return False

    def _estimate_duration(self, text: str) -> float:
        words = max(1, len(text.split()))
        duration = (words / self.words_per_minute) * 60.0
        return max(3.0, duration)

    def _write_fallback_audio(self, out_path: Path, duration_seconds: float) -> None:
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
                value = amplitude * envelope * math.sin((2.0 * math.pi * frequency * index) / sample_rate)
                frames.extend(struct.pack("<h", int(32767.0 * value)))
            wav_file.writeframes(bytes(frames))

    @staticmethod
    def _write_pcm_as_wav(out_path: Path, pcm_bytes: bytes, sample_rate: int) -> None:
        with wave.open(str(out_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_bytes)
