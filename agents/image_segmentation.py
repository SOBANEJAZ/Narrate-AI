"""Image Segmentation Agent.

This agent analyzes the narration script and determines where images
should change. It identifies natural breakpoints based on:
- Topic shifts (different subjects)
- Location changes (different places)
- Time period changes (different eras)
- Mood shifts (dramatic moments)

Each zone maps to a specific range of sentences that will be paired
with a single image throughout the video.

Agent Type: LLM-based (Groq API)
Model: llama-3.3-70b-versatile
"""

from groq import Groq

import json

from core.models import ImageSegmentation


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM did not return JSON.")
    depth = 0
    for i, char in enumerate(text[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("LLM did not return valid JSON.")


def segment_for_images(context, script: str):
    """Analyze script and determine optimal image placement zones.

    The agent reads through the script and identifies "visual boundaries" -
    points where changing the image would improve storytelling.

    Output is a list of zones, each containing:
    - start_sentence: First sentence (1-indexed)
    - end_sentence: Last sentence
    - description: Brief noun phrase describing ideal image

    The placement service later maps these zones to actual segments
    and generates image search queries for each.

    Args:
        context: Dict with 'groq_client' and 'config' keys
        script: Full documentary script text

    Returns:
        ImageSegmentation Pydantic model with zone boundaries

    Example:
        Script: "The Apollo program began in 1961..."
                 "President Kennedy announced the challenge..."
                 "The Saturn V rocket was developed..."

        Zones might be:
        - Zone 1: sentences 1-2, description: "Kennedy 1961"
        - Zone 2: sentences 3-3, description: "Saturn V rocket"
    """
    print(
        f"[IMAGE SEGMENT] Analyzing script for image placement ({len(script.split())} words)",
        flush=True,
    )

    groq_client = context["groq_client"]

    prompt = f"""You are a documentary visual editor. Segment the script into image zones so each zone can be illustrated by one strong image.

Task:
- Split by visual meaning, not just equal length
- Change zones at clear boundaries: new subject, place, time, actor, event, or consequence
- Keep continuity where ideas are tightly connected

Zone constraints:
- 2 to 3 sentences per zone
- Zones must be sequential and fully cover the script from sentence 1 to the final sentence
- No overlaps, no gaps
- zone_id must start at 1 and increase by 1

Description constraints (critical for image retrieval):
- 2 to 6 words
- Concrete noun phrase, not a full sentence
- Prefer specific entities/time/place when available
- Avoid vague labels like "historical scene", "people talking", "important event"
- Good examples: "Napoleon at Waterloo", "Berlin Wall 1989", "Saturn V launch"

Output format (STRICT):
- Return ONLY valid JSON (no markdown, no explanation)
- Use exactly:
{{
  "zones": [
    {{
      "zone_id": 1,
      "start_sentence": 1,
      "end_sentence": 3,
      "description": "..."
    }}
  ]
}}

Script:
{script}
"""

    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.3,  # Low temp for consistent zone boundaries
    )

    content = response.choices[0].message.content
    json_data = extract_json(content)
    segmentation = ImageSegmentation.model_validate(json_data)

    print(
        f"[IMAGE SEGMENT] Created {len(segmentation.zones)} image zones",
        flush=True,
    )
    for zone in segmentation.zones:
        print(
            f"  - Zone {zone.zone_id}: sentences {zone.start_sentence}-{zone.end_sentence} | {zone.description}",
            flush=True,
        )

    return segmentation
