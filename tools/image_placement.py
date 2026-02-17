"""Image placement agent."""

from core.models import create_script_segment
from core.text_utils import split_sentences


def build_segments(script, sentence_span=3):
    """Build script segments by grouping sentences."""
    sentences = split_sentences(script)
    print(
        f"[SEGMENT] Split script into {len(sentences)} sentences (span={sentence_span})",
        flush=True,
    )
    if not sentences:
        return []

    segments = []
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
