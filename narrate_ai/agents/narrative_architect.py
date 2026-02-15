"""Narrative architect agent using functional programming style."""

from ..llm import generate_json
from ..models import create_narrative_plan, create_narrative_section


def build_narrative_plan(client, topic):
    """Build a narrative plan for the given topic."""
    print(f"[NARRATIVE] Building narrative plan for topic: {topic}", flush=True)

    fallback_sections = [
        create_narrative_section(
            title="Introduction",
            objective=f"Introduce {topic} and set historical context.",
            duration_seconds=30,
        ),
        create_narrative_section(
            title="Main Content",
            objective=f"Explain key aspects and developments of {topic}.",
            duration_seconds=60,
        ),
        create_narrative_section(
            title="Conclusion",
            objective=f"Conclude with summary and legacy of {topic}.",
            duration_seconds=30,
        ),
    ]

    fallback = {
        "tone": "documentary",
        "pacing": "steady",
        "target_duration_seconds": 120,
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
- Durations should total around 2 minutes (120 seconds).
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
    sections = []
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
