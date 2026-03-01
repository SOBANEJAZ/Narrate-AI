"""Narrative Architect Agent.

This agent is responsible for creating the structural plan for a documentary.
It analyzes the topic and determines:
- Overall narrative arc (intro, body, conclusion)
- Section structure (3-4 main sections)
- Tone and pacing style
- Target duration for each section

The plan serves as a blueprint for script writing and image selection.

Agent Type: LLM-based (Groq API)
Model: openai/gpt-oss-20b
"""

from groq import Groq

from core.llm import extract_json, validate_pydantic, LLMError
from core.models import NarrativePlan, NarrativeSection


def build_narrative_plan(context, topic):
    """Build a narrative plan for the given topic.

    This is the first step in the pipeline. The agent analyzes the topic
    and creates a structured outline with sections, each having:
    - title: Engaging name for the section
    - objective: What this section should cover
    - duration_seconds: Target length

    The plan guides all subsequent steps:
    - Query generation uses section objectives
    - Script writing follows the section structure
    - Image selection matches section themes

    Args:
        context: Dict with 'groq_client' and 'config' keys
        topic: Documentary topic string

    Returns:
        NarrativePlan Pydantic model with sections and metadata

    Raises:
        ValueError: If plan has no sections
    """
    print(f"[NARRATIVE] Building narrative plan for topic: {topic}", flush=True)

    groq_client = context["groq_client"]
    config = context["config"]

    # System prompt explaining the agent's role and outputs
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
        temperature=0.2,  # Low temp for consistent, structured output
    )

    json_data = extract_json(response.choices[0].message.content)
    plan = validate_pydantic(json_data, NarrativePlan)

    # Ensure minimum duration per section (at least 15 seconds)
    for section in plan.sections:
        section.duration_seconds = max(15, section.duration_seconds)

    if not plan.sections:
        raise ValueError("Generated plan has no sections")

    print(
        f"[NARRATIVE] Plan ready: {len(plan.sections)} sections, target {plan.target_duration_seconds}s",
        flush=True,
    )
    return plan
