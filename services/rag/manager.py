"""RAG (Retrieval-Augmented Generation) module using Pinecone and Qwen3 embeddings."""

import hashlib
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from pydantic import BaseModel


PINECONE_INDEX_NAME = "narrate-ai"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
EMBEDDING_DIMENSION = 1024


class PineconeManager:
    """Manager for Pinecone vector database operations."""

    def __init__(self, api_key: str, environment: str = "us-east-1"):
        self.api_key = api_key
        self.environment = environment
        self.pc = Pinecone(api_key=api_key)

    def create_index_if_not_exists(self, namespace: str = None) -> str:
        """Create the single index if it doesn't exist, or recreate if dimension mismatch."""
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
        """Delete all vectors in a namespace."""
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
        """Index research notes into Pinecone."""
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

            embedding = embed_text(text, topic)
            if embedding is None:
                continue

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
        """Retrieve relevant notes for a query."""
        index_name = self.create_index_if_not_exists()

        if index_name not in self.pc.list_indexes().names():
            print(f"[RAG] Index {index_name} does not exist")
            return []

        index = self.pc.Index(index_name)

        query_embedding = embed_text(query, topic)
        if query_embedding is None:
            print("[RAG] Failed to embed query")
            return []

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
    """Embed text using Qwen3 local embedding model."""
    model = SentenceTransformer(EMBEDDING_MODEL)
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def create_pinecone_manager(config: dict) -> PineconeManager | None:
    """Create Pinecone manager from config."""
    api_key = config.get("pinecone_api_key")
    if not api_key:
        print("[RAG] PINECONE_API_KEY not set")
        return None

    environment = config.get("pinecone_environment", "us-east-1")
    return PineconeManager(api_key=api_key, environment=environment)
