"""RAG (Retrieval-Augmented Generation) module using Pinecone and Gemini embeddings."""

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

try:
    from google import genai
except ImportError:
    genai = None

try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    Pinecone = None


PINECONE_INDEX_NAME = "narrate-ai"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 3072


class PineconeManager:
    """Manager for Pinecone vector database operations."""

    def __init__(self, api_key: str, environment: str = "us-east-1"):
        if Pinecone is None:
            raise ImportError("pinecone package not installed")
        self.api_key = api_key
        self.environment = environment
        self.pc = Pinecone(api_key=api_key)

    def create_index_if_not_exists(self, namespace: str) -> str:
        """Create a new index for the given namespace."""
        index_name = f"{PINECONE_INDEX_NAME}-{namespace}"

        if index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=index_name,
                dimension=EMBEDDING_DIMENSION,
                spec=ServerlessSpec(cloud="aws", region=self.environment),
            )
            print(f"[RAG] Created new Pinecone index: {index_name}")

        return index_name

    def delete_index(self, namespace: str):
        """Delete the index for the given namespace."""
        index_name = f"{PINECONE_INDEX_NAME}-{namespace}"
        if index_name in self.pc.list_indexes().names():
            self.pc.delete_index(index_name)
            print(f"[RAG] Deleted Pinecone index: {index_name}")

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

        index_name = f"{PINECONE_INDEX_NAME}-{namespace}"
        if index_name not in self.pc.list_indexes().names():
            index_name = self.create_index_if_not_exists(namespace)

        index = self.pc.Index(index_name)

        vectors = []
        for note in notes:
            text = note.get("text", "")
            if not text:
                continue

            embedding = embed_text(text, topic)
            if embedding is None:
                continue

            vector_id = f"{note.get('source_url', 'unknown')}-{note.get('chunk_id', 0)}"

            vectors.append(
                {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "source_url": note.get("source_url", ""),
                        "chunk_id": note.get("chunk_id", 0),
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
        index_name = f"{PINECONE_INDEX_NAME}-{namespace}"

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
                    "chunk_id": match.metadata.get("chunk_id", 0),
                    "text": match.metadata.get("text", ""),
                    "score": match.score,
                }
            )

        print(
            f"[RAG] Retrieved {len(retrieved_notes)} notes for query: {query[:50]}..."
        )
        return retrieved_notes


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float] | None:
    """Embed text using Gemini embedding model."""
    if genai is None:
        print("[RAG] google-genai not installed, using fallback")
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[RAG] GEMINI_API_KEY not set, using fallback")
        return None

    try:
        client = genai.Client(api_key=api_key)
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"[RAG] Error embedding text: {e}")
        return None


def create_pinecone_manager(config: dict) -> PineconeManager | None:
    """Create Pinecone manager from config."""
    api_key = config.get("pinecone_api_key")
    if not api_key:
        print("[RAG] PINECONE_API_KEY not set")
        return None

    environment = config.get("pinecone_environment", "us-east-1")
    return PineconeManager(api_key=api_key, environment=environment)
