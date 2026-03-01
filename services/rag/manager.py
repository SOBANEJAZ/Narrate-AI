"""RAG (Retrieval-Augmented Generation) Service.

This module provides vector database operations using:
- Pinecone: Cloud vector database for similarity search
- MiniLM-L12-v2: Local embedding model for text vectorization

RAG Workflow:
1. Index phase: Research notes are converted to embeddings and stored
2. Query phase: Search queries are embedded and compared to find similar notes

The system uses namespaces to isolate different topics in the same index.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from pydantic import BaseModel

# Suppress verbose transformer library logs
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("safetensors").setLevel(logging.ERROR)


PINECONE_INDEX_NAME = "narrate-ai"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384
_model = None  # Global singleton for embedding model


class PineconeManager:
    """Manager for Pinecone vector database operations.

    Handles:
    - Index creation and management
    - Note indexing (upserting vectors)
    - Note retrieval (similarity search)
    - Namespace cleanup

    Pinecone is optional - if API key is missing, the pipeline
    falls back to using raw notes directly.
    """

    def __init__(self, api_key: str, environment: str = "us-east-1"):
        self.api_key = api_key
        self.environment = environment
        self.pc = Pinecone(api_key=api_key)

    def create_index_if_not_exists(self, namespace: str = None) -> str:
        """Create the Pinecone index if it doesn't exist.

        If index exists but has wrong dimension, deletes and recreates.
        Uses serverless spec for pay-per-request pricing.

        Args:
            namespace: Not used, kept for API compatibility

        Returns:
            Name of the index
        """
        indexes = self.pc.list_indexes()

        if PINECONE_INDEX_NAME in indexes.names():
            existing_index = self.pc.describe_index(PINECONE_INDEX_NAME)
            if existing_index.dimension != EMBEDDING_DIMENSION:
                print(
                    f"[RAG] Dimension mismatch: existing={existing_index.dimension}, expected={EMBEDDING_DIMENSION}. Deleting and recreating index..."
                )
                self.pc.delete_index(PINECONE_INDEX_NAME)
            else:
                return PINECONE_INDEX_NAME

        self.pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            spec=ServerlessSpec(cloud="aws", region=self.environment),
        )
        print(
            f"[RAG] Created Pinecone index: {PINECONE_INDEX_NAME} (dim={EMBEDDING_DIMENSION})"
        )

        return PINECONE_INDEX_NAME

    def clear_namespace(self, namespace: str):
        """Delete all vectors in a namespace.

        Called after retrieval to clean up temporary index data.

        Args:
            namespace: Namespace to clear
        """
        index = self.pc.Index(PINECONE_INDEX_NAME)
        try:
            index.delete(delete_all=True, namespace=namespace)
            print(f"[RAG] Cleared namespace: {namespace}")
        except Exception as e:
            print(f"[RAG] Warning: Could not clear namespace {namespace}: {e}")

    def index_notes(
        self,
        namespace: str,
        notes: list[dict[str, Any]],
        topic: str,
    ) -> str:
        """Index research notes into Pinecone vector database.

        Converts each note to an embedding vector and stores it with
        metadata (source_url, text, topic) for retrieval.

        Args:
            namespace: Pinecone namespace (typically slugified topic)
            notes: List of research note dicts
            topic: Topic string for metadata

        Returns:
            The namespace used
        """
        if not notes:
            print("[RAG] No notes to index")
            return ""

        index_name = self.create_index_if_not_exists()
        index = self.pc.Index(index_name)

        vectors = []
        for note in notes:
            text = note.get("text", "")
            if not text:
                continue

            # Convert text to embedding vector
            embedding = embed_text(text, topic)
            if embedding is None:
                continue

            # Create unique ID from source URL + text hash
            vector_id = f"{note.get('source_url', 'unknown')}-{hashlib.md5(text.encode()).hexdigest()[:8]}"

            vectors.append(
                {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "source_url": note.get("source_url", ""),
                        "text": text,
                        "topic": topic,
                    },
                }
            )

        if vectors:
            index.upsert(vectors=vectors, namespace=namespace)
            print(f"[RAG] Indexed {len(vectors)} notes to namespace: {namespace}")

        return namespace

    def retrieve_notes(
        self,
        namespace: str,
        query: str,
        topic: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant notes for a semantic search query.

        Embeds the query and finds the most similar notes using
        cosine similarity in vector space.

        Args:
            namespace: Namespace to search in
            query: Search query string
            topic: Topic for embedding task type
            top_k: Number of results to return

        Returns:
            List of retrieved note dicts with source_url, text, score
        """
        index_name = self.create_index_if_not_exists()

        if index_name not in self.pc.list_indexes().names():
            print(f"[RAG] Index {index_name} does not exist")
            return []

        index = self.pc.Index(index_name)

        # Embed the search query
        query_embedding = embed_text(query, topic)
        if query_embedding is None:
            print("[RAG] Failed to embed query")
            return []

        # Similarity search
        results = index.query(
            namespace=namespace,
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
        )

        retrieved_notes = []
        for match in results.matches:
            retrieved_notes.append(
                {
                    "source_url": match.metadata.get("source_url", ""),
                    "text": match.metadata.get("text", ""),
                    "score": match.score,
                }
            )

        print(
            f"[RAG] Retrieved {len(retrieved_notes)} notes for query: {query[:50]}..."
        )
        return retrieved_notes


def embed_text(text: str, task_type: str = "RETRIEVAL_QUERY") -> list[float] | None:
    """Embed text using MiniLM local embedding model.

    Uses sentence-transformers library to convert text to 384-dimensional
    embedding vector. Model is cached globally for efficiency.

    Args:
        text: Text to embed
        task_type: Task type hint (passed to model but not heavily used)

    Returns:
        List of 384 floats (embedding vector) or None on error
    """
    global _model
    if _model is None:
        print(
            "[RAG] Loading MiniLM embedding model (first run - downloading if needed)..."
        )
        _model = SentenceTransformer(EMBEDDING_MODEL)
    embedding = _model.encode(text, normalize_embeddings=True, show_progress_bar=False)
    return embedding.tolist()


def create_pinecone_manager(config: dict) -> PineconeManager | None:
    """Create Pinecone manager from pipeline configuration.

    Returns None if PINECONE_API_KEY is not set, allowing the
    pipeline to fall back to direct note usage.

    Args:
        config: Pipeline configuration dict

    Returns:
        PineconeManager instance or None
    """
    api_key = config.get("pinecone_api_key")
    if not api_key:
        print("[RAG] PINECONE_API_KEY not set")
        return None

    environment = config.get("pinecone_environment", "us-east-1")
    return PineconeManager(api_key=api_key, environment=environment)
