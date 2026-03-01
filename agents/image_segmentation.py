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

from core.llm import extract_json
from core.models import ImageSegmentation


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

    prompt = f"""You are an expert at analyzing documentary scripts to determine optimal image placement.

Given the script below, analyze it and determine where images should change to best illustrate the content.

Consider:
- Topic shifts (e.g., from historical context to specific events)
- Location changes (different places should show different images)
- Time period changes (different eras need different imagery)
- Mood shifts (dramatic moments may need different imagery)
- Key visual moments (specific people, places, or events mentioned)

Guidelines:
- Minimum 2 sentences per image zone (don't fragment too much)
- Maximum 4 sentences per image zone (keep images fresh)
- Each zone needs a brief description (2-5 words) of what the image should show
- The description should be a concise noun phrase (e.g., "Viet Minh soldiers", "Saigon 1975", "Vietnam map")

IMPORTANT: Return ONLY valid JSON. No markdown, no explanations.

Script:
{script}

Output as JSON with this structure:
{{
    "zones": [
        {{
            "zone_id": 1,
            "start_sentence": 1,
            "end_sentence": 3,
            "description": "brief image description"
        }}
    ]
}}

Make sure zones are sequential with no gaps in sentence numbers.
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
