"""Image Placement Service.

This module converts the LLM-generated image segmentation into
actual script segments that can be processed by downstream services.

It maps zone boundaries (sentence numbers) to actual text content,
creating segments that pair well-defined script portions with images.
"""

import re

from core.models import ImageSegmentation, create_script_segment


def split_sentences(text: str) -> list[str]:
    """Split text into sentences.

    Handles common sentence endings (. ! ?) followed by whitespace.
    Also normalizes multiple whitespace to single spaces first.

    Args:
        text: Input text to split

    Returns:
        List of sentences (empty if input is empty)
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    return [
        item.strip() for item in re.split(r"(?<=[.!?])\s+", cleaned) if item.strip()
    ]


def build_segments(script, segmentation: ImageSegmentation):
    """Build script segments based on LLM-generated image zones.

    Takes the full script and segmentation zones, then:
    1. Splits script into sentences
    2. Maps each zone to its corresponding sentence range
    3. Creates segment dicts with text content

    Handles edge cases:
    - Zone starts outside script range (skip)
    - Zone ends beyond script (cap to script length)

    Args:
        script: Full documentary script text
        segmentation: ImageSegmentation from image segmentation agent

    Returns:
        List of script segment dicts with text and sentence ranges
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
        # Convert to 0-indexed for array access
        start_idx = zone.start_sentence - 1
        end_idx = zone.end_sentence

        # Validate start position
        if start_idx < 0 or start_idx >= len(sentences):
            print(
                f"[SEGMENT] Zone {zone.zone_id}: start_sentence {zone.start_sentence} out of range, skipping",
                flush=True,
            )
            continue

        # Cap end position to script length
        if end_idx > len(sentences):
            end_idx = len(sentences)
            print(
                f"[SEGMENT] Zone {zone.zone_id}: end_sentence {zone.end_sentence} exceeds total, capped to {end_idx}",
                flush=True,
            )

        # Extract text for this zone
        zone_sentences = sentences[start_idx:end_idx]
        zone_text = " ".join(zone_sentences)

        segments.append(
            create_script_segment(
                segment_id=zone.zone_id,
                text=zone_text,
                start_sentence=zone.start_sentence,
                end_sentence=end_idx,
                search_queries=[zone.description],
            )
        )

    print(
        f"[SEGMENT] Built {len(segments)} visual segments from image zones", flush=True
    )
    return segments
