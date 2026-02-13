from __future__ import annotations

from dataclasses import dataclass

from ..llm import LLMClient
from ..models import NarrativePlan, NarrativeSection


@dataclass(slots=True)
class NarrativeArchitectAgent:
    llm: LLMClient

    def build_plan(self, topic: str) -> NarrativePlan:
        print(f"[NARRATIVE] Building narrative plan for topic: {topic}", flush=True)
        fallback_sections = [
            NarrativeSection("Introduction", f"Introduce {topic} and set historical context.", 35),
            NarrativeSection("Origins", f"Explain how {topic} began and key early milestones.", 55),
            NarrativeSection("Turning Points", f"Describe major shifts in {topic}.", 65),
            NarrativeSection("Legacy", f"Conclude with long-term impact of {topic}.", 45),
        ]
        fallback = {
            "tone": "documentary",
            "pacing": "steady",
            "target_duration_seconds": 200,
            "sections": [
                {
                    "title": section.title,
                    "objective": section.objective,
                    "duration_seconds": section.duration_seconds,
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
        plan_json = self.llm.generate_json(
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
                    NarrativeSection(
                        title=str(entry["title"]).strip(),
                        objective=str(entry["objective"]).strip(),
                        duration_seconds=max(15, int(entry["duration_seconds"])),
                    )
                )
            except Exception:
                continue

        if not sections:
            sections = fallback_sections

        target_duration = sum(section.duration_seconds for section in sections)
        plan = NarrativePlan(
            topic=topic,
            tone=str(plan_json.get("tone", "documentary")),
            pacing=str(plan_json.get("pacing", "steady")),
            target_duration_seconds=int(plan_json.get("target_duration_seconds", target_duration)),
            sections=sections,
        )
        print(
            f"[NARRATIVE] Plan ready: {len(plan.sections)} sections, target {plan.target_duration_seconds}s",
            flush=True,
        )
        return plan
