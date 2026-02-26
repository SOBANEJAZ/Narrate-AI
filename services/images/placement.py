"""Image placement agent."""

from core.models import ImageSegmentation, create_script_segment
from core.text_utils import split_sentences


def build_segments(script, segmentation: ImageSegmentation):
    """Build script segments based on LLM-generated image zones.

    Args:
        script: The full documentary script text
        segmentation: ImageSegmentation from the image segmentation agent

    Returns:
        List of script segments matching the image zones
    """
    sentences = split_sentences(script)
    print(
        f"[SEGMENT] Split script into {len(sentences)} sentences",
        flush=True,
    )
    if not sentences:
        return []

    segments = []
    for zone in segmentation.zones:
        start_idx = zone.start_sentence - 1
        end_idx = zone.end_sentence

        if start_idx < 0 or start_idx >= len(sentences):
            print(
                f"[SEGMENT] Zone {zone.zone_id}: start_sentence {zone.start_sentence} out of range, skipping",
                flush=True,
            )
            continue

        if end_idx > len(sentences):
            end_idx = len(sentences)
            print(
                f"[SEGMENT] Zone {zone.zone_id}: end_sentence {zone.end_sentence} exceeds total, capped to {end_idx}",
                flush=True,
            )

        zone_sentences = sentences[start_idx:end_idx]
        zone_text = " ".join(zone_sentences)

        segments.append(
            create_script_segment(
                segment_id=zone.zone_id,
                text=zone_text,
                start_sentence=zone.start_sentence,
                end_sentence=end_idx,
                visual_description=zone.description,
            )
        )

    print(
        f"[SEGMENT] Built {len(segments)} visual segments from image zones", flush=True
    )
    return segments
