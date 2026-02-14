"""Narrative architect agent using functional programming style."""

from __future__ import annotations

from ..llm import LLMClientState, generate_json
from ..models import (
    NarrativePlan,
    NarrativeSection,
    create_narrative_plan,
    create_narrative_section,
)


def build_narrative_plan(client: LLMClientState, topic: str) -> NarrativePlan:
    """Build a narrative plan for the given topic.

    Args:
        client: LLM client state
        topic: Documentary topic

    Returns:
        NarrativePlan with sections and metadata
    """
    print(f"[NARRATIVE] Building narrative plan for topic: {topic}", flush=True)

    fallback_sections = [
        create_narrative_section(
            title="Introduction",
            objective=f"Introduce {topic} and set historical context.",
            duration_seconds=35,
        ),
        create_narrative_section(
            title="Origins",
            objective=f"Explain how {topic} began and key early milestones.",
            duration_seconds=55,
        ),
        create_narrative_section(
            title="Turning Points",
            objective=f"Describe major shifts in {topic}.",
            duration_seconds=65,
        ),
        create_narrative_section(
            title="Legacy",
            objective=f"Conclude with long-term impact of {topic}.",
            duration_seconds=45,
        ),
    ]

    fallback = {
        "tone": "documentary",
        "pacing": "steady",
        "target_duration_seconds": 200,
        "sections": [
            {
                "title": section["title"],
                "objective": section["objective"],
                "duration_seconds": section["duration_seconds"],
            }
            for section in fallback_sections
        ],
    }

    prompt = f"""
You are the Narrative Architect for a documentary system.
Topic: {topic}

Return strict JSON with keys:
- tone: short string
- pacing: short string
- target_duration_seconds: integer
- sections: list of 4-6 objects with title, objective, duration_seconds

Constraints:
- Build a clear story arc with introduction, core sections, transitions, and conclusion.
- Durations should total around 3 to 6 minutes.
"""
    plan_json = generate_json(
        client,
        prompt,
        provider="groq",
        fallback_json=fallback,
        temperature=0.2,
        max_tokens=700,
    )

    raw_sections = plan_json.get("sections", fallback["sections"])
    sections: list[NarrativeSection] = []
    for entry in raw_sections:
        try:
            sections.append(
                create_narrative_section(
                    title=str(entry["title"]).strip(),
                    objective=str(entry["objective"]).strip(),
                    duration_seconds=max(15, int(entry["duration_seconds"])),
                )
            )
        except Exception:
            continue

    if not sections:
        sections = fallback_sections

    target_duration = sum(section["duration_seconds"] for section in sections)
    plan = create_narrative_plan(
        topic=topic,
        tone=str(plan_json.get("tone", "documentary")),
        pacing=str(plan_json.get("pacing", "steady")),
        target_duration_seconds=int(
            plan_json.get("target_duration_seconds", target_duration)
        ),
        sections=sections,
    )
    print(
        f"[NARRATIVE] Plan ready: {len(plan['sections'])} sections, target {plan['target_duration_seconds']}s",
        flush=True,
    )
    return plan
