from __future__ import annotations

from dataclasses import dataclass

from ..llm import LLMClient
from ..models import NarrativePlan, ResearchNote


@dataclass(slots=True)
class ScriptWriterAgent:
    llm: LLMClient

    def write_script(self, topic: str, plan: NarrativePlan, notes: list[ResearchNote]) -> str:
        print(
            f"[SCRIPT] Writing script for '{topic}' using {len(notes)} research notes",
            flush=True,
        )
        context_notes = "\n".join(
            f"- [{note.source_url}] {note.text}" for note in notes[:20]
        )

        section_brief = "\n".join(
            f"{index + 1}. {section.title} ({section.duration_seconds}s): {section.objective}"
            for index, section in enumerate(plan.sections)
        )
        fallback_script = self._build_fallback_script(topic, plan, notes)

        prompt = f"""
You are the Script Writing Agent for a historical documentary.

Topic: {topic}
Tone: {plan.tone}
Pacing: {plan.pacing}
Target duration: {plan.target_duration_seconds} seconds

Section plan:
{section_brief}

Research notes:
{context_notes}

Write a single flowing narration script:
- spoken-language style
- vivid but factual
- avoid academic stiffness
- include smooth transitions between sections
- no markdown headings
"""

        script = self.llm.generate_text(
            prompt,
            provider="cerebras",
            fallback_text=fallback_script,
            temperature=0.55,
            max_tokens=2200,
        )
        print(
            f"[SCRIPT] Script ready: {len(script.split())} words",
            flush=True,
        )
        return script

    def _build_fallback_script(
        self, topic: str, plan: NarrativePlan, notes: list[ResearchNote]
    ) -> str:
        snippets = [note.text for note in notes[:12]]
        stitched = " ".join(snippets)
        if not stitched:
            stitched = (
                f"This documentary explores {topic}. The story begins with the origins, "
                "moves through major turning points, and closes with long-term impact."
            )

        sections: list[str] = []
        for index, section in enumerate(plan.sections):
            start = index * 180
            stop = start + 220
            section_evidence = stitched[start:stop].strip()
            if not section_evidence:
                section_evidence = stitched[:220]
            sections.append(
                f"{section.title}. {section.objective} "
                f"{section_evidence} "
                "This moment connects directly to the next chapter in the story."
            )
        return " ".join(sections)
