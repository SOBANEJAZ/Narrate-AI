"""Narrate-AI package."""

from .core.config import (
    create_config_from_env,
    create_default_config,
    get_resolution,
    update_config,
)
from .core.models import (
    NarrativePlan,
    NarrativeSection,
    PlanQueries,
    ResearchNote,
    SectionQuery,
    VisualIntelligence,
    create_image_candidate,
    create_narrative_plan,
    create_narrative_section,
    create_research_note,
    create_research_source,
    create_script_segment,
    create_timeline_item,
)
from .pipeline import run_pipeline

__all__ = [
    "create_default_config",
    "create_config_from_env",
    "get_resolution",
    "update_config",
    "create_narrative_section",
    "create_narrative_plan",
    "create_research_source",
    "create_research_note",
    "create_image_candidate",
    "create_script_segment",
    "create_timeline_item",
    "run_pipeline",
    "NarrativePlan",
    "NarrativeSection",
    "VisualIntelligence",
    "PlanQueries",
    "SectionQuery",
    "ResearchNote",
]
