"""Script Writer Agent.

This agent writes the actual narration script for the documentary.
It uses:
- The narrative plan (structure, tone, pacing)
- Retrieved research notes (context from RAG)
- Its own knowledge (primary source)

The script is written in spoken-language style suitable for narration,
not formal written prose.

Agent Type: LLM-based (Groq API)
Model: meta-llama/llama-4-scout-17b-16e-instruct
"""

from groq import Groq

from core.models import NarrativePlan


def write_script(context, topic: str, plan: NarrativePlan, retrieved_notes: list[dict]):
    """Write a documentary script based on the plan and retrieved research notes.

    This is the core content generation step. The agent:
    1. Uses its own knowledge as the primary source (more complete)
    2. Uses research notes for verification and additional facts
    3. Writes in spoken-language style (for TTS narration)
    4. Follows the section structure from the narrative plan

    The output is plain text (no markdown) suitable for:
    - Text-to-speech synthesis
    - Image segmentation (finding breakpoints)
    - Timeline creation

    Args:
        context: Dict with 'groq_client' and 'config' keys
        topic: Documentary topic string
        plan: NarrativePlan with section structure
        retrieved_notes: List of relevant notes from RAG

    Returns:
        Plain text script suitable for narration
    """
    print(
        f"[SCRIPT] Writing script for '{topic}' using {len(retrieved_notes)} retrieved notes",
        flush=True,
    )

    groq_client = context["groq_client"]
    config = context["config"]

    # Build section brief for the prompt
    section_brief = "\n".join(
        f"- {section.title} ({section.duration_seconds}s): {section.objective}"
        for section in plan.sections
    )

    # Include research notes as supplementary context
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

    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0.55,  # Higher temp for more natural, engaging writing
    )

    script = response.choices[0].message.content
    print(
        f"[SCRIPT] Script ready: {len(script.split())} words",
        flush=True,
    )
    return script
