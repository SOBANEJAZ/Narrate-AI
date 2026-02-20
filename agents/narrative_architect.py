"""Narrative architect agent."""

from groq import Groq

from core.llm import extract_json, validate_pydantic, LLMError
from core.models import NarrativePlan, NarrativeSection


def build_narrative_plan(context, topic):
    """Build a narrative plan for the given topic.

    Args:
        context: Dict with 'groq_client' and 'config' keys
        topic: Documentary topic string

    Returns a NarrativePlan Pydantic model.
    """
    print(f"[NARRATIVE] Building narrative plan for topic: {topic}", flush=True)

    groq_client = context["groq_client"]
    config = context["config"]

    prompt = f"""
You are the Narrative Architect for Narrate-AI, a documentary generator that creates slideshow-style educational videos. Your role is to structure the documentary content into a compelling narrative flow.

Context:
- Narrate-AI produces documentary videos by combining narration audio with relevant images
- Each section will be illustrated with images retrieved and ranked using OpenCLIP
- The final video displays images centered on screen with subtle zoom effects over time
- Target audience expects historically accurate and visually compelling content
- Each section will have its own image search queries and visual descriptions generated
- The script will be written based on your structural plan and supporting research notes

Topic: {topic}

Return strict JSON with:
- topic: the documentary topic string
- tone: short string describing the documentary tone (e.g., "educational", "historical", "informative", "narrative")
- pacing: short string describing the pacing style (e.g., "steady", "methodical", "dynamic", "thoughtful")
- target_duration_seconds: integer representing total video duration
- sections: list of 3-4 objects with title, objective, duration_seconds

Constraints:
- Build a clear story arc with introduction, core sections, transitions, and conclusion
- Durations should total around 2 minutes (120 seconds) unless topic complexity requires adjustment
- Section titles should be engaging and descriptive enough to guide image search and visual content
- Section objectives should be specific enough to guide script writing and image selection
- Consider how each section will translate to visual content for the audience
"""

    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="openai/gpt-oss-20b",
        temperature=0.2,
    )

    json_data = extract_json(response.choices[0].message.content)
    plan = validate_pydantic(json_data, NarrativePlan)

    for section in plan.sections:
        section.duration_seconds = max(15, section.duration_seconds)

    if not plan.sections:
        raise ValueError("Generated plan has no sections")

    print(
        f"[NARRATIVE] Plan ready: {len(plan.sections)} sections, target {plan.target_duration_seconds}s",
        flush=True,
    )
    return plan
