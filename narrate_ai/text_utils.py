from __future__ import annotations

import re
from collections import Counter


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
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    return [
        item.strip() for item in re.split(r"(?<=[.!?])\s+", cleaned) if item.strip()
    ]


def chunk_text(
    text: str, chunk_size_words: int = 180, overlap_words: int = 30
) -> list[str]:
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
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]+", text.lower())
    filtered = [word for word in words if word not in STOPWORDS and len(word) > 2]
    freq = Counter(filtered)
    return [word for word, _ in freq.most_common(limit)]


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "topic"


def safe_filename(name: str, max_length: int = 100) -> str:
    """Sanitize and truncate a filename to avoid 'File name too long' errors.

    Args:
        name: Original filename (may include extension)
        max_length: Maximum allowed length for the filename (default 100)

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
