"""Script writer agent using functional programming style."""

from ..llm import generate_text
from ..models import NarrativePlan


def write_script(client, topic: str, plan: NarrativePlan, retrieved_notes: list[dict]):
    """Write a documentary script based on the plan and retrieved research notes.

    The script is generated using the LLM's own knowledge as the primary source,
    with research notes as supplementary context for verification and enrichment.

    Args:
        client: LLM client
        topic: Documentary topic
        plan: NarrativePlan Pydantic model
        retrieved_notes: List of retrieved notes from RAG (already filtered/relevant)

    Returns:
        Generated script text
    """
    print(
        f"[SCRIPT] Writing script for '{topic}' using {len(retrieved_notes)} retrieved notes",
        flush=True,
    )

    section_brief = "\n".join(
        f"- {section.title} ({section.duration_seconds}s): {section.objective}"
        for section in plan.sections
    )

    context_notes = "\n".join(
        f"- [{note.get('source_url', 'unknown')}] {note.get('text', '')}"
        for note in retrieved_notes
    )

    prompt = f"""You are a documentary script writer for Narrate-AI, a system that creates slideshow-style educational videos. Your role is to write an engaging, historically accurate narration script that will be paired with relevant images.

Context:
- Narrate-AI produces documentary videos by combining narration audio with relevant images
- Each section of your script will be illustrated with images retrieved using search queries and ranked using OpenCLIP
- The final video displays images centered on screen with subtle zoom effects over time
- Target audience expects historically accurate and visually compelling content
- Images will be selected based on visual descriptions generated from your script segments
- The script should be engaging when viewed alongside supporting imagery

Topic: {topic}

STRUCTURE (use this as your outline):
{section_brief}

TARGET DURATION: {plan.target_duration_seconds} seconds
TONE: {plan.tone}
PACING: {plan.pacing}

WRITING INSTRUCTIONS:
1. Write the script primarily using YOUR OWN KNOWLEDGE as the base
2. The research notes below are ONLY for additional context and verification
3. Do NOT rely solely on the notes - use your knowledge to fill gaps
4. If notes contain relevant facts, you may incorporate them naturally
5. Write in a spoken-language style, vivid but factual - keep in mind that this will be narrated aloud
6. Include smooth transitions between sections that help maintain visual continuity
7. No markdown headings - just flowing prose suitable for voiceover narration
8. Consider how each sentence will translate to visual content - make references concrete enough for image matching
9. Maintain the documentary tone and pacing specified above
10. Ensure historical accuracy while keeping the content engaging for viewers

RESEARCH NOTES (supplementary):
{context_notes}

Now write the complete documentary narration script:
"""

    script = generate_text(
        client,
        prompt,
        provider="cerebras",
        fallback_text=_fallback_script(topic, plan),
        temperature=0.55,
    )
    print(
        f"[SCRIPT] Script ready: {len(script.split())} words",
        flush=True,
    )
    return script


def _fallback_script(topic: str, plan: NarrativePlan) -> str:
    """Fallback script when LLM fails."""
    sections = "\n".join(
        f"## {section.title}\n\n{section.objective}" for section in plan.sections
    )
    return f"""Welcome to this documentary about {topic}.

{sections}

This concludes our documentary on {topic}. Thank you for watching."""
