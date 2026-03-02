"""Services package - domain-specific utilities for Narrate-AI.

This package contains service modules for different domains:
- audio_generator: TTS and narration synthesis
- image_placement: Script segmentation for images
- image_ranking: CLIP-based image ranking
- image_retrieval: Image search and download
- rag_manager: Pinecone vector database operations
- research_crawler: Web crawling and source discovery
- video_assembly: Video assembly and timeline building
"""

from .audio_generator import (
    create_tts_synthesizer,
    get_available_voices,
    synthesize_audio,
    synthesize_with_edge_tts,
    synthesize_with_elevenlabs,
)
from .image_placement import build_segments
from .image_ranking import create_ranking_state, rank_images
from .image_retrieval import retrieve_images
from .rag_manager import PineconeManager, create_pinecone_manager
from .research_crawler import crawl_and_build_notes, discover_sources
from .video_assembly import assemble_video, build_timeline

__all__ = [
    # Audio
    "synthesize_with_elevenlabs",
    "synthesize_with_edge_tts",
    "create_tts_synthesizer",
    "get_available_voices",
    "synthesize_audio",
    # Images
    "build_segments",
    "create_ranking_state",
    "rank_images",
    "retrieve_images",
    # RAG
    "PineconeManager",
    "create_pinecone_manager",
    # Research
    "crawl_and_build_notes",
    "discover_sources",
    # Video
    "assemble_video",
    "build_timeline",
]
