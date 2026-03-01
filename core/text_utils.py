"""Text processing utilities.

Provides common text manipulation functions used across the pipeline:
- Sentence splitting
- Text chunking for RAG
- Keyword extraction
- String normalization (slugify, safe filenames)

These are low-level utilities that don't depend on external services.
"""

from __future__ import annotations

import re
from collections import Counter


# Common English stopwords to filter out during keyword extraction
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
}


def split_sentences(text: str) -> list[str]:
    """Split text into sentences.

    Handles common sentence endings (. ! ?) followed by whitespace.
    Also normalizes multiple whitespace to single spaces first.

    Args:
        text: Input text to split

    Returns:
        List of sentences (empty if input is empty)
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    return [
        item.strip() for item in re.split(r"(?<=[.!?])\s+", cleaned) if item.strip()
    ]


def chunk_text(
    text: str, chunk_size_words: int = 180, overlap_words: int = 30
) -> list[str]:
    """Split text into overlapping chunks of words.

    Used for preparing text for RAG indexing. The overlap ensures
    context is preserved at chunk boundaries.

    Example:
        chunk_text("hello world foo bar", chunk_size_words=2, overlap_words=1)
        # Returns: ["hello world", "world foo bar"]

    Args:
        text: Input text to chunk
        chunk_size_words: Maximum words per chunk (default 180)
        overlap_words: Words to overlap between chunks (default 30)

    Returns:
        List of text chunks
    """
    words = text.split()
    if not words:
        return []
    if chunk_size_words <= overlap_words:
        overlap_words = 0

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_size_words)
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(words):
            break
        start = end - overlap_words
    return chunks


def extract_keywords(text: str, limit: int = 8) -> list[str]:
    """Extract most common meaningful words from text.

    Filters out:
    - Stopwords (the, a, is, etc.)
    - Very short words (< 3 chars)
    - Non-alphanumeric characters

    Used for generating search queries and image search terms.

    Args:
        text: Input text
        limit: Maximum keywords to return (default 8)

    Returns:
        List of most common keywords, sorted by frequency
    """
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]+", text.lower())
    filtered = [word for word in words if word not in STOPWORDS and len(word) > 2]
    freq = Counter(filtered)
    return [word for word, _ in freq.most_common(limit)]


def slugify(value: str) -> str:
    """Convert text to a URL-safe slug.

    Replaces non-alphanumeric characters with hyphens and converts to lowercase.
    Leading/trailing hyphens are removed.

    Example:
        slugify("Hello World!") -> "hello-world"
        slugify("Apollo 11") -> "apollo-11"

    Args:
        value: Input text

    Returns:
        Slugified string (or "topic" if empty result)
    """
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "topic"


def safe_filename(name: str, max_length: int = 100) -> str:
    """Sanitize and truncate a filename to avoid filesystem errors.

    Removes unsafe characters and ensures the filename doesn't exceed
    the maximum length. Attempts to preserve file extensions when truncating.

    Args:
        name: Original filename (may include extension)
        max_length: Maximum allowed length (default 100)

    Returns:
        Safe filename truncated to max_length characters
    """
    # Keep only safe characters
    safe = "".join(ch for ch in name if ch.isalnum() or ch in {".", "_", "-"})
    if not safe:
        safe = "unnamed"
    # Ensure we don't exceed max_length
    if len(safe) > max_length:
        # Try to preserve extension if present
        if "." in safe:
            parts = safe.rsplit(".", 1)
            stem, ext = parts[0], parts[1]
            ext_len = len(ext) + 1  # +1 for the dot
            max_stem = max_length - ext_len
            if max_stem > 0:
                safe = f"{stem[:max_stem]}.{ext}"
            else:
                safe = safe[:max_length]
        else:
            safe = safe[:max_length]
    return safe
