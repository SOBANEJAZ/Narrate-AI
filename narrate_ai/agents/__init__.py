"""Agents module exports."""

from .narrative_architect import build_narrative_plan
from .query_generator import generate_section_queries
from .script_writer import write_script
from .visual_intelligence import enrich_segments
from ..tools.image_placement import build_segments
from ..tools.image_ranking import create_ranking_state, rank_images
from ..tools.image_retrieval import retrieve_images
from ..tools.narration import synthesize_audio
from ..tools.research import crawl_and_build_notes, discover_sources

__all__ = [
    "build_narrative_plan",
    "discover_sources",
    "crawl_and_build_notes",
    "write_script",
    "build_segments",
    "enrich_segments",
    "retrieve_images",
    "create_ranking_state",
    "rank_images",
    "synthesize_audio",
    "generate_section_queries",
]
