"""Services package - domain-specific utilities for Narrate-AI.

This package contains service modules for different domains:
- rag: Vector database and semantic search via Pinecone
- media: TTS, narration, and video assembly
- research: Web discovery and content crawling
- images: Image retrieval, ranking, and placement
"""

__all__ = [
    # Import submodules on-demand to avoid circular dependencies
    "rag",
    "media",
    "research",
    "images",
]
