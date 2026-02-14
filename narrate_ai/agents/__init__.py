"""Agents module exports (functional programming style)."""

from .image_placement import build_segments
from .image_ranking import create_ranking_state, rank_images
from .image_retrieval import retrieve_images
from .narration import synthesize_audio
from .narrative_architect import build_narrative_plan
from .research import crawl_and_build_notes, discover_sources
from .script_writer import write_script
from .visual_intelligence import enrich_segments

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
]
