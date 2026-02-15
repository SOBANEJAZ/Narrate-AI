"""Query generator agent for RAG - generates search queries from narrative plan."""

from ..llm import generate_pydantic
from ..models import PlanQueries, SectionQuery


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
You are a query generation agent for a documentary RAG system.
Given the narrative plan, generate semantic search queries to retrieve relevant research notes.

Topic: {plan.topic}
Tone: {plan.tone}

Sections:
{sections_brief}

For each section, generate a search query that will help retrieve the most relevant 
research notes from a vector database. The query should be:
- Concise (2-6 keywords)
- Focused on the specific aspect of the topic covered in that section
- Optimized for semantic search

Return JSON with:
- queries: list of objects with section_title, section_objective, and search_query
"""

    result = generate_pydantic(
        client,
        prompt=prompt,
        provider="groq",
        model=PlanQueries,
        temperature=0.3,
        max_tokens=500,
    )

    if result is None:
        print("[QUERY] Failed to generate queries, using fallback", flush=True)
        return _fallback_queries(plan)

    print(f"[QUERY] Generated {len(result.queries)} search queries", flush=True)
    return result


def _fallback_queries(plan):
    """Create fallback queries when LLM fails."""
    queries = []
    for section in plan.sections:
        queries.append(
            SectionQuery(
                section_title=section.title,
                section_objective=section.objective,
                search_query=f"{plan.topic} {section.title}".lower(),
            )
        )
    return PlanQueries(queries=queries)
