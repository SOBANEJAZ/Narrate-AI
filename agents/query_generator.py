"""Query Generator Agent for RAG.

This agent generates semantic search queries for each narrative section.
These queries are used to retrieve relevant research notes from the
vector database (Pinecone) to provide context for script writing.

Why separate from script writer?
- Allows focused, specific queries per section
- Enables retrieval of diverse sources
- Improves RAG accuracy by generating query-specific queries

Agent Type: LLM-based (Groq API)
Model: openai/gpt-oss-20b
"""

from groq import Groq

import json

from core.models import PlanQueries, SectionQuery


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM did not return JSON.")
    depth = 0
    for i, char in enumerate(text[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("LLM did not return valid JSON.")


def generate_section_queries(context, plan):
    """Generate semantic search queries for each section of the narrative plan.

    Takes the narrative plan (sections with titles and objectives) and
    generates optimized search queries for each. These queries are designed
    to retrieve the most relevant context from the vector database.

    The queries should be:
    - Concise (2-6 keywords) for better semantic matching
    - Focused on the specific aspect of that section
    - Different from each other to ensure diverse source retrieval

    Args:
        context: Dict with 'groq_client' and 'config' keys
        plan: NarrativePlan Pydantic model with sections

    Returns:
        PlanQueries Pydantic model containing queries for each section
    """
    print(
        f"[QUERY] Generating search queries for {len(plan.sections)} sections",
        flush=True,
    )

    groq_client = context["groq_client"]
    config = context["config"]

    # Create brief summary of each section for the prompt
    sections_brief = "\n".join(
        f"- {section.title}: {section.objective}" for section in plan.sections
    )

    prompt = f"""
You are a retrieval-query specialist for Narrate-AI. Generate high-signal semantic queries for each section so vector search returns factual, section-specific evidence.

Topic: {plan.topic}
Tone: {plan.tone}

Sections:
{sections_brief}

Goal:
- Produce ONE query per section that is precise enough to avoid generic matches
- Queries should maximize factual retrieval (dates, people, places, events, mechanisms, outcomes)

Query-writing rules:
- 3-10 words each
- Include concrete anchors when possible: names, years, locations, event names, institutions
- Avoid vague fillers ("history", "overview", "important facts", "introduction")
- Keep each query distinct from the others; minimize overlap
- Match each section's objective directly

Output format (STRICT):
- Return ONLY valid JSON, no markdown or explanation
- JSON shape:
  {{
    "queries": [
      {{
        "section_title": "...",
        "section_objective": "...",
        "search_query": "..."
      }}
    ]
  }}

Integrity constraints:
- Keep section_title and section_objective aligned to the provided section list
- Number of query objects must equal the number of provided sections
"""

    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="openai/gpt-oss-20b",
        temperature=0.3,  # Moderate temp for creative but focused queries
    )

    json_data = extract_json(response.choices[0].message.content)
    result = PlanQueries.model_validate(json_data)

    print(f"[QUERY] Generated {len(result.queries)} search queries", flush=True)
    return result
