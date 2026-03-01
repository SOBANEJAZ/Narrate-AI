"""Caching module for expensive operations.

This module provides a two-layer caching system:
1. Memory cache - Fast, ephemeral, lost on restart
2. Disk cache - Persistent, survives restarts

Used for:
- Web search results (research, images)
- Crawled web page content
- Any expensive operation that should only run once

The cache is organized by namespace to avoid key collisions.
For example: "research:sources::apollo program" and "crawl:page::https://..."
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any


class MultiLayerCache:
    """Two-layer cache: memory (fast) + filesystem (persistent).

    This avoids re-fetching from APIs or re-crawling websites on subsequent
    runs with the same topic. The memory layer provides instant access
    for repeated lookups within a single pipeline run.

    Example usage:
        cache = MultiLayerCache(Path("runs/cache"))

        # Check if cached
        cached_sources = cache.get("research", "sources::apollo program")
        if cached_sources is None:
            sources = fetch_sources()
            cache.set("research", "sources::apollo program", sources)

    Namespace examples:
    - "research": Source discovery results
    - "crawl": Crawled web page content
    - "images": Image search results
    """

    def __init__(self, root: Path) -> None:
        """Initialize cache with root directory.

        Args:
            root: Base directory for disk cache (created if needed)
        """
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._memory: dict[str, Any] = {}

    def _hash_key(self, namespace: str, key: str) -> str:
        """Create a safe filename-safe hash from namespace and key.

        Args:
            namespace: Cache namespace (e.g., "research", "crawl")
            key: Cache key (e.g., "sources::apollo program")

        Returns:
            SHA256 hash hex string (truncated for filename safety)
        """
        raw = f"{namespace}:{key}".encode("utf-8")
        return sha256(raw).hexdigest()

    def _path(self, namespace: str, key: str) -> Path:
        """Get the filesystem path for a cached item.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            Path to JSON cache file
        """
        namespace_dir = self.root / namespace
        namespace_dir.mkdir(parents=True, exist_ok=True)
        return namespace_dir / f"{self._hash_key(namespace, key)}.json"

    def get(self, namespace: str, key: str) -> Any | None:
        """Retrieve a value from cache (memory first, then disk).

        Checks memory cache first for speed, falls back to disk cache.
        If found on disk, loads into memory for faster subsequent access.

        Args:
            namespace: Cache namespace (e.g., "research", "images")
            key: Cache key (e.g., "sources::topic")

        Returns:
            Cached value if found, None if not cached
        """
        memory_key = f"{namespace}:{key}"
        if memory_key in self._memory:
            return self._memory[memory_key]

        path = self._path(namespace, key)
        if not path.exists():
            return None

        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            self._memory[memory_key] = value
            return value
        except json.JSONDecodeError:
            return None

    def set(self, namespace: str, key: str, value: Any) -> None:
        """Store a value in cache (memory and disk).

        Writes to both memory (instant access) and disk (persistent).
        JSON serialization is automatic.

        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache (must be JSON-serializable)
        """
        memory_key = f"{namespace}:{key}"
        self._memory[memory_key] = value
        path = self._path(namespace, key)
        path.write_text(
            json.dumps(value, ensure_ascii=True, indent=2), encoding="utf-8"
        )
