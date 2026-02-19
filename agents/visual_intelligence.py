"""Visual intelligence agent."""

from core.llm import generate_pydantic
from core.models import VisualIntelligence
from core.text_utils import extract_keywords


def enrich_segments(client, topic, segments, max_queries_per_segment=5):
    """Enrich segments with search queries and visual descriptions."""
    print(
        f"[VISUAL] Generating search queries + descriptions for {len(segments)} segments",
        flush=True,
    )
    for segment in segments:
        prompt = f"""
You are a visual intelligence module for Narrate-AI, a documentary generator that creates slideshow-style educational videos. Your role is to generate image search queries and visual descriptions that will be used to find and rank relevant images for each script segment.

Context:
- Narrate-AI produces documentary videos by combining narration audio with relevant images
- Images are retrieved using DuckDuckGo Search (DDGS) based on your search queries
- Images are ranked using OpenCLIP (semantic similarity between your visual description and the actual image content)
- The final video displays images centered on screen with subtle zoom effects over time
- Target audience expects historically accurate and visually compelling content

Topic: {topic}
Segment text: {segment["text"]}

Return strict JSON with:
- search_queries: list of up to {max_queries_per_segment} specific, historically accurate image search queries optimized for DDGS
- visual_description: one rich, concrete, descriptive sentence that captures the key visual elements for OpenCLIP semantic matching

Requirements:
- Search queries should be specific to historical entities, events, people, places, objects, or visual elements mentioned in the segment
- Search queries should be optimized for image search engines (avoid abstract concepts, focus on concrete nouns)
- Visual description should be detailed and specific enough for OpenCLIP to accurately match relevant images
- Visual description should focus on what the viewer should see (people, places, objects, scenes, actions)
- Both search queries and visual descriptions should align with the documentary tone and historical accuracy
- Prioritize historically significant visual elements that would engage viewers
"""
        generated = generate_pydantic(
            client,
            prompt=prompt,
            model=VisualIntelligence,
            temperature=0.25,
            model_override=client["config"]["groq_model"],
        )

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
