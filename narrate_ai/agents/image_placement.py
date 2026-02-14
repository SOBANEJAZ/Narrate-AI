"""Image placement agent using functional programming style."""

from __future__ import annotations

from ..models import ScriptSegment, create_script_segment
from ..text_utils import split_sentences


def build_segments(
    script: str,
    sentence_span: int = 3,
) -> list[ScriptSegment]:
    """Build script segments by grouping sentences.

    Args:
        script: Full script text
        sentence_span: Number of sentences per segment

    Returns:
        List of script segments
    """
    sentences = split_sentences(script)
    print(
        f"[SEGMENT] Split script into {len(sentences)} sentences (span={sentence_span})",
        flush=True,
    )
    if not sentences:
        return []

    segments: list[ScriptSegment] = []
    segment_id = 1
    for idx in range(0, len(sentences), sentence_span):
        chunk = sentences[idx : idx + sentence_span]
        segments.append(
            create_script_segment(
                segment_id=segment_id,
                text=" ".join(chunk),
                start_sentence=idx + 1,
                end_sentence=idx + len(chunk),
            )
        )
        segment_id += 1
    print(f"[SEGMENT] Built {len(segments)} visual segments", flush=True)
    return segments
