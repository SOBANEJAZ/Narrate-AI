"""Query generator agent for RAG - generates search queries from narrative plan."""

from core.llm import generate_pydantic
from core.models import PlanQueries, SectionQuery


def generate_section_queries(client, plan):
    """Generate semantic search queries for each section of the narrative plan.

    Args:
        client: LLM client
        plan: NarrativePlan Pydantic model

    Returns:
        PlanQueries Pydantic model with queries for each section
    """
    print(
        f"[QUERY] Generating search queries for {len(plan.sections)} sections",
        flush=True,
    )

    sections_brief = "\n".join(
        f"- {section.title}: {section.objective}" for section in plan.sections
    )

    prompt = f"""
You are a query generation agent for Narrate-AI, a documentary generator that creates slideshow-style educational videos. Your role is to generate semantic search queries that will retrieve the most relevant research notes from a vector database to support each section of the documentary.

Context:
- Narrate-AI produces documentary videos by combining narration audio with relevant images
- Research notes retrieved by your queries will be used to enrich the script with factual details
- Each section will be illustrated with images retrieved and ranked using OpenCLIP
- The final video displays images centered on screen with subtle zoom effects over time
- Target audience expects historically accurate and visually compelling content

Topic: {plan.topic}
Tone: {plan.tone}

Sections:
{sections_brief}

For each section, generate a search query that will help retrieve the most relevant
research notes from a vector database. The query should be:
- Concise (2-6 keywords)
- Focused on the specific aspect of the topic covered in that section
- Optimized for semantic search
- Aligned with the documentary's educational and historical accuracy goals

Return JSON with:
- queries: list of objects with section_title, section_objective, and search_query
"""

    result = generate_pydantic(
        client,
        prompt=prompt,
        provider="groq",
        model=PlanQueries,
        temperature=0.3,
    )

    print(f"[QUERY] Generated {len(result.queries)} search queries", flush=True)
    return result
