"""Visual intelligence agent using functional programming style."""

from ..llm import generate_pydantic
from ..models import VisualIntelligence
from ..text_utils import extract_keywords


def enrich_segments(client, topic, segments, max_queries_per_segment=5):
    """Enrich segments with search queries and visual descriptions."""
    print(
        f"[VISUAL] Generating search queries + descriptions for {len(segments)} segments",
        flush=True,
    )
    for segment in segments:
        fallback = _fallback(topic, segment["text"], max_queries_per_segment)
        prompt = f"""
You are a visual intelligence module for a documentary generator.
Topic: {topic}
Segment text: {segment["text"]}

Return strict JSON with:
- search_queries: list of up to {max_queries_per_segment} keyword-optimized image search queries
- visual_description: one descriptive natural sentence for OpenCLIP matching

Requirements:
- search queries should be historically specific entities/events
- visual description should be rich and concrete, written as one sentence
"""
        generated = generate_pydantic(
            client,
            prompt=prompt,
            provider="groq",
            model=VisualIntelligence,
            temperature=0.25,
            max_tokens=500,
        )

        if generated is None:
            generated = fallback

        clean_queries = []
        for query in generated.search_queries:
            query_str = str(query).strip()
            if query_str:
                clean_queries.append(query_str)

        segment["search_queries"] = clean_queries[:max_queries_per_segment]
        segment["visual_description"] = str(generated.visual_description).strip()
        print(
            f"[VISUAL] Segment {segment['segment_id']}: {len(segment['search_queries'])} queries generated",
            flush=True,
        )
    return segments


def _fallback(topic, text, max_queries_per_segment):
    """Create fallback search queries and description."""
    keywords = extract_keywords(text, limit=10)
    query_base = " ".join(keywords[:4]) if keywords else topic
    queries = [
        f"{topic} {query_base} historical photograph",
        f"{topic} {query_base} archive image",
        f"{topic} timeline event illustration",
        f"{topic} documentary still",
        f"{topic} black and white photo",
    ]
    description = f"A historically grounded documentary image about {topic}, showing {text[:220].strip()}."
    return VisualIntelligence(
        search_queries=queries[:max_queries_per_segment],
        visual_description=description,
    )
