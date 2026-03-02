"""Narrative Architect Agent.

This agent is responsible for creating the structural plan for a documentary.
It analyzes the topic and determines:
- Overall narrative arc (intro, body, conclusion)
- Section structure (3-4 main sections)
- Tone and pacing style
- Target duration for each section

The plan serves as a blueprint for script writing and image selection.

Agent Type: LLM-based (Groq API)
Model: openai/gpt-oss-20b
"""

from groq import Groq

import json

from core.models import NarrativePlan, NarrativeSection


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


def build_narrative_plan(context, topic):
    """Build a narrative plan for the given topic.

    This is the first step in the pipeline. The agent analyzes the topic
    and creates a structured outline with sections, each having:
    - title: Engaging name for the section
    - objective: What this section should cover
    - duration_seconds: Target length

    The plan guides all subsequent steps:
    - Query generation uses section objectives
    - Script writing follows the section structure
    - Image selection matches section themes

    Args:
        context: Dict with 'groq_client' and 'config' keys
        topic: Documentary topic string

    Returns:
        NarrativePlan Pydantic model with sections and metadata

    Raises:
        ValueError: If plan has no sections
    """
    print(f"[NARRATIVE] Building narrative plan for topic: {topic}", flush=True)

    groq_client = context["groq_client"]
    config = context["config"]

    # System prompt explaining the agent's role and outputs
    prompt = f"""
You are the Narrative Architect for Narrate-AI. Build a concise, documentary-grade narrative plan for the topic below.

Topic: {topic}

Production context:
- The final output is a slideshow-style documentary with narration and changing images
- Each section will later generate semantic research queries and image search terms
- Strong plans are factual, chronological/logical, and visually concrete

Your job:
1. Design a clear narrative arc: setup -> development -> turning point(s) -> consequence/legacy
2. Keep sections specific and non-overlapping (avoid repeating the same idea)
3. Prefer concrete entities/time/place details so downstream image retrieval is easier

Output requirements (STRICT):
- Return ONLY one valid JSON object, no markdown, no prose, no code fences
- Use exactly this shape and field names:
  - topic: string
  - tone: short string
  - pacing: short string
  - target_duration_seconds: integer
  - sections: array of 3-4 objects, each with:
    - title: string
    - objective: string
    - duration_seconds: integer

Quality constraints:
- target_duration_seconds should be about 120 seconds unless topic complexity justifies 100-150
- Sum of section durations should be close to target_duration_seconds
- Each section objective must be one sentence, specific, and actionable for script writing
- Titles must be distinct and documentary-appropriate (not generic labels like "Overview")
- Ensure beginning and ending sections are clearly identifiable from titles/objectives
"""

    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="openai/gpt-oss-20b",
        temperature=0.2,  # Low temp for consistent, structured output
    )

    json_data = extract_json(response.choices[0].message.content)
    plan = NarrativePlan.model_validate(json_data)

    # Ensure minimum duration per section (at least 15 seconds)
    for section in plan.sections:
        section.duration_seconds = max(15, section.duration_seconds)

    if not plan.sections:
        raise ValueError("Generated plan has no sections")

    print(
        f"[NARRATIVE] Plan ready: {len(plan.sections)} sections, target {plan.target_duration_seconds}s",
        flush=True,
    )
    return plan
