"""Narrate-AI package (functional programming style)."""

from .config import (
    PipelineConfig,
    create_config_from_env,
    create_default_config,
    get_resolution,
    update_config,
)
from .models import (
    ImageCandidate,
    NarrativePlan,
    NarrativeSection,
    ResearchNote,
    ResearchSource,
    ScriptSegment,
    TimelineItem,
    create_image_candidate,
    create_narrative_plan,
    create_narrative_section,
    create_research_note,
    create_research_source,
    create_script_segment,
    create_timeline_item,
)
from .pipeline import PipelineResult, run_pipeline

__all__ = [
    "PipelineConfig",
    "create_default_config",
    "create_config_from_env",
    "get_resolution",
    "update_config",
    "NarrativeSection",
    "NarrativePlan",
    "ResearchSource",
    "ResearchNote",
    "ImageCandidate",
    "ScriptSegment",
    "TimelineItem",
    "create_narrative_section",
    "create_narrative_plan",
    "create_research_source",
    "create_research_note",
    "create_image_candidate",
    "create_script_segment",
    "create_timeline_item",
    "run_pipeline",
    "PipelineResult",
]
