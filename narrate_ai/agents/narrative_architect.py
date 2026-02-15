"""Narrative architect agent using functional programming style."""

from ..llm import generate_pydantic
from ..models import NarrativePlan, NarrativeSection


def build_narrative_plan(client, topic):
    """Build a narrative plan for the given topic.

    Returns a NarrativePlan Pydantic model.
    """
    print(f"[NARRATIVE] Building narrative plan for topic: {topic}", flush=True)

    fallback_sections = [
        NarrativeSection(
            title="Introduction",
            objective=f"Introduce {topic} and set historical context.",
            duration_seconds=30,
        ),
        NarrativeSection(
            title="Main Content",
            objective=f"Explain key aspects and developments of {topic}.",
            duration_seconds=60,
        ),
        NarrativeSection(
            title="Conclusion",
            objective=f"Conclude with summary and legacy of {topic}.",
            duration_seconds=30,
        ),
    ]

    fallback_plan = NarrativePlan(
        topic=topic,
        tone="documentary",
        pacing="steady",
        target_duration_seconds=120,
        sections=fallback_sections,
    )

    prompt = f"""
You are the Narrative Architect for a documentary system.
Topic: {topic}

Return strict JSON with:
- tone: short string
- pacing: short string  
- target_duration_seconds: integer
- sections: list of 3-4 objects with title, objective, duration_seconds

Constraints:
- Build a clear story arc with introduction, core sections, transitions, and conclusion.
- Durations should total around 2 minutes (120 seconds).
"""

    plan = generate_pydantic(
        client,
        prompt=prompt,
        provider="groq",
        model=NarrativePlan,
        temperature=0.2,
        max_tokens=700,
    )

    if plan is None:
        print("[NARRATIVE] Failed to generate plan, using fallback", flush=True)
        plan = fallback_plan
    else:
        for section in plan.sections:
            section.duration_seconds = max(15, section.duration_seconds)

        if not plan.sections:
            plan.sections = fallback_sections

    print(
        f"[NARRATIVE] Plan ready: {len(plan.sections)} sections, target {plan.target_duration_seconds}s",
        flush=True,
    )
    return plan
