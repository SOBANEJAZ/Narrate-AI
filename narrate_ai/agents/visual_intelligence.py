from __future__ import annotations

from dataclasses import dataclass

from ..llm import LLMClient
from ..models import ScriptSegment
from ..text_utils import extract_keywords


@dataclass(slots=True)
class VisualIntelligenceAgent:
    llm: LLMClient
    max_queries_per_segment: int = 5

    def enrich_segments(self, topic: str, segments: list[ScriptSegment]) -> list[ScriptSegment]:
        print(
            f"[VISUAL] Generating search queries + descriptions for {len(segments)} segments",
            flush=True,
        )
        for segment in segments:
            fallback = self._fallback(topic, segment.text)
            prompt = f"""
You are a visual intelligence module for a documentary generator.
Topic: {topic}
Segment text: {segment.text}

Return strict JSON with fields:
- search_queries: list of up to {self.max_queries_per_segment} keyword-optimized image search queries
- visual_description: one descriptive natural sentence for OpenCLIP matching

Requirements:
- search queries should be historically specific entities/events
- visual description should be rich and concrete, written as one sentence
"""
            generated = self.llm.generate_json(
                prompt,
                provider="groq",
                fallback_json=fallback,
                temperature=0.25,
                max_tokens=500,
            )
            queries = generated.get("search_queries") or fallback["search_queries"]
            visual_description = generated.get("visual_description") or fallback["visual_description"]

            clean_queries: list[str] = []
            for query in queries:
                query_str = str(query).strip()
                if query_str:
                    clean_queries.append(query_str)
            segment.search_queries = clean_queries[: self.max_queries_per_segment]
            segment.visual_description = str(visual_description).strip()
            print(
                f"[VISUAL] Segment {segment.segment_id}: {len(segment.search_queries)} queries generated",
                flush=True,
            )
        return segments

    def _fallback(self, topic: str, text: str) -> dict[str, object]:
        keywords = extract_keywords(text, limit=10)
        query_base = " ".join(keywords[:4]) if keywords else topic
        queries = [
            f"{topic} {query_base} historical photograph",
            f"{topic} {query_base} archive image",
            f"{topic} timeline event illustration",
            f"{topic} documentary still",
            f"{topic} black and white photo",
        ]
        description = (
            f"A historically grounded documentary image about {topic}, showing {text[:220].strip()}."
        )
        return {"search_queries": queries[: self.max_queries_per_segment], "visual_description": description}
