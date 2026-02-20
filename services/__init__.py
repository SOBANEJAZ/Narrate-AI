"""Services package - domain-specific utilities for Narrate-AI.

This package contains service modules for different domains:
- rag: Vector database and semantic search via Pinecone
- audio: TTS and narration synthesis
- video: Video assembly and timeline building
- research: Web discovery and content crawling
- images: Image retrieval, ranking, and placement
"""

__all__ = [
    # Import submodules on-demand to avoid circular dependencies
    "rag",
    "audio",
    "video",
    "research",
    "images",
]
