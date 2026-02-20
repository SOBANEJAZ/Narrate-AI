"""RAG (Retrieval-Augmented Generation) service using Pinecone and Gemini embeddings."""

from services.rag.manager import PineconeManager, create_pinecone_manager

__all__ = ["PineconeManager", "create_pinecone_manager"]
