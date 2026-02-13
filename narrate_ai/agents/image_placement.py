from __future__ import annotations

from dataclasses import dataclass

from ..models import ScriptSegment
from ..text_utils import split_sentences


@dataclass(slots=True)
class ImagePlacementAgent:
    sentence_span: int = 3

    def build_segments(self, script: str) -> list[ScriptSegment]:
        sentences = split_sentences(script)
        print(
            f"[SEGMENT] Split script into {len(sentences)} sentences (span={self.sentence_span})",
            flush=True,
        )
        if not sentences:
            return []

        segments: list[ScriptSegment] = []
        segment_id = 1
        for idx in range(0, len(sentences), self.sentence_span):
            chunk = sentences[idx : idx + self.sentence_span]
            segments.append(
                ScriptSegment(
                    segment_id=segment_id,
                    text=" ".join(chunk),
                    start_sentence=idx + 1,
                    end_sentence=idx + len(chunk),
                )
            )
            segment_id += 1
        print(f"[SEGMENT] Built {len(segments)} visual segments", flush=True)
        return segments
