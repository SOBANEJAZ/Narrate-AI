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

    prompt = f"""You are a senior documentary narration writer for Narrate-AI. Write one continuous voiceover script that is compelling, accurate, and visually concrete.

Topic: {topic}
Target duration: {plan.target_duration_seconds} seconds
Tone: {plan.tone}
Pacing: {plan.pacing}

Required outline (follow this progression):
{section_brief}

Production constraints:
- Script will be narrated with TTS and paired with changing images
- Each part should include concrete visual anchors (people, places, artifacts, events, dates)
- Avoid abstract-only passages that are hard to illustrate

Writing rules:
1. Primary source is your general knowledge; research notes are supplemental evidence
2. Prioritize factual reliability; if a detail is uncertain, use cautious phrasing instead of inventing precision
3. Write natural spoken prose (no bullet points, no markdown headings, no citations)
4. Use smooth transitions so section boundaries feel coherent
5. Maintain narrative momentum: setup, development, stakes, consequence, takeaway
6. Vary sentence length for listenability, but keep wording clear and concise
7. Keep chronology and causality explicit when relevant
8. Prefer specific nouns/verbs over vague language

Length guidance:
- Aim for roughly {int(plan.target_duration_seconds * 2.2)} to {int(plan.target_duration_seconds * 2.8)} words total
- Keep coverage balanced across sections according to their durations

RESEARCH NOTES (supplementary context, may be partial/noisy):
{context_notes}

Return only the final narration script text.
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
