"""Image Retrieval Service.

This module handles:
1. Image search - Using Serper.dev Google Images API
2. Parallel downloading - Multiple images fetched concurrently
3. Caching - Avoid re-downloading previously fetched images

Each segment gets its own directory with candidate images that
are later ranked by the ranking service.
"""

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from core.models import create_image_candidate


class MultiLayerCache:
    """Two-layer cache: memory (fast) + filesystem (persistent)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._memory: dict[str, Any] = {}

    def _hash_key(self, namespace: str, key: str) -> str:
        raw = f"{namespace}:{key}".encode("utf-8")
        return sha256(raw).hexdigest()

    def _path(self, namespace: str, key: str) -> Path:
        namespace_dir = self.root / namespace
        namespace_dir.mkdir(parents=True, exist_ok=True)
        return namespace_dir / f"{self._hash_key(namespace, key)}.json"

    def get(self, namespace: str, key: str) -> Any | None:
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
        memory_key = f"{namespace}:{key}"
        self._memory[memory_key] = value
        path = self._path(namespace, key)
        path.write_text(
            json.dumps(value, ensure_ascii=True, indent=2), encoding="utf-8"
        )


SERPERS_IMAGES_URL = "https://google.serper.dev/images"

MAX_IMAGE_DOWNLOAD_WORKERS = 8  # Parallel download threads


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
    safe = "".join(ch for ch in name if ch.isalnum() or ch in {".", "_", "-"})
    if not safe:
        safe = "unnamed"
    if len(safe) > max_length:
        if "." in safe:
            parts = safe.rsplit(".", 1)
            stem, ext = parts[0], parts[1]
            ext_len = len(ext) + 1
            max_stem = max_length - ext_len
            if max_stem > 0:
                safe = f"{stem[:max_stem]}.{ext}"
            else:
                safe = safe[:max_length]
        else:
            safe = safe[:max_length]
    return safe


def retrieve_images(config, cache, segments, images_root):
    """Retrieve candidate images for all script segments.

    For each segment:
    1. Search using segment's image queries (via Serper.dev)
    2. Download images in parallel
    3. Store as candidate images for ranking

    Uses caching to avoid redundant API calls and downloads.

    Args:
        config: Pipeline configuration
        cache: Cache instance for search results
        segments: List of script segment dicts
        images_root: Root directory for downloaded images

    Returns:
        Segments dict with candidate_images added
    """
    print(
        f"[IMAGES] Retrieving images for {len(segments)} segments",
        flush=True,
    )
    images_root.mkdir(parents=True, exist_ok=True)
    seen_urls = set()  # Avoid duplicate images across segments

    for segment in segments:
        segment_id = segment["segment_id"]
        segment_dir = images_root / f"segment_{segment_id:03d}"
        segment_dir.mkdir(parents=True, exist_ok=True)
        print(
            f"[IMAGES] Segment {segment_id}: running {len(segment.get('search_queries', []))} queries",
            flush=True,
        )

        candidates = []
        queries = segment.get("search_queries", [])[: config["max_queries_per_segment"]]

        urls_to_download = []

        # Search for each query and collect unique image URLs
        for query in queries:
            results = _search_images_with_client(config, cache, query)
            print(
                f"[IMAGES] Segment {segment_id}: query '{query}' returned {len(results)} results",
                flush=True,
            )

            for item in results:
                image_url = str(
                    item.get("imageUrl") or item.get("image") or item.get("url") or ""
                ).strip()
                if not image_url or image_url in seen_urls:
                    continue
                seen_urls.add(image_url)
                title = str(item.get("title") or item.get("source") or "image").strip()
                source = str(item.get("source") or item.get("url") or "").strip()
                urls_to_download.append(
                    {
                        "url": image_url,
                        "title": title,
                        "source": source,
                    }
                )

        # Download images in parallel
        if urls_to_download:
            print(
                f"[IMAGES] Segment {segment_id}: downloading {len(urls_to_download)} images in parallel",
                flush=True,
            )
            with ThreadPoolExecutor(max_workers=MAX_IMAGE_DOWNLOAD_WORKERS) as executor:
                futures = {
                    executor.submit(
                        _download_image_worker,
                        config,
                        item["url"],
                        item["title"],
                        item["source"],
                        segment_dir,
                        segment_id,
                    ): item
                    for item in urls_to_download
                }
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        candidates.append(result)

        segment["candidate_images"] = candidates
        print(
            f"[IMAGES] Segment {segment_id}: downloaded {len(candidates)} candidates",
            flush=True,
        )
    return segments


def _download_image_worker(config, url, title, source, segment_dir, segment_id):
    """Download a single image from URL.

    Checks cache first (file existence), downloads if needed.
    Validates content-type to ensure it's actually an image.

    Args:
        config: Pipeline configuration
        url: Image URL to download
        title: Image title/description
        source: Source website
        segment_dir: Directory to save image
        segment_id: For logging

    Returns:
        ImageCandidate dict or None if download failed
    """
    file_name = _filename_from_url(url, prefix="img")
    path = segment_dir / file_name

    # Use cached file if exists
    if path.exists():
        return create_image_candidate(
            url=url,
            title=title,
            source=source,
            local_path=path,
        )

    try:
        response = requests.get(
            url,
            timeout=(3, 10),  # Connect timeout, read timeout
            headers={"User-Agent": "Narrate-AI/1.0"},
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type:
            print(f"[IMAGES] Segment {segment_id}: skipped non-image content: {url}")
            return None
        path.write_bytes(response.content)
        return create_image_candidate(
            url=url,
            title=title,
            source=source,
            local_path=path,
        )
    except requests.RequestException as exc:
        print(f"[IMAGES] Segment {segment_id}: failed to download {url}: {exc}")
        return None


def _search_images(config, cache, query):
    """Search for images using Serper.dev Google Images API.

    Results are cached to avoid redundant API calls.

    Args:
        config: Pipeline configuration
        cache: Cache instance
        query: Search query string

    Returns:
        List of image result dicts from Serper
    """
    cache_key = f"images::{query.lower()}"
    cached = cache.get("images", cache_key)
    if isinstance(cached, list):
        return [item for item in cached if isinstance(item, dict)]

    serper_api_key = str(config.get("serper_api_key") or "").strip()
    if not serper_api_key:
        raise RuntimeError(
            "Missing SERPER_API_KEY. Set it in your environment or .env file."
        )

    headers = {
        "X-API-KEY": serper_api_key,
        "Content-Type": "application/json",
    }
    payload = {"q": query}
    response = requests.post(
        SERPERS_IMAGES_URL,
        headers=headers,
        json=payload,
        timeout=config["request_timeout_seconds"],
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        error_text = response.text.strip()
        detail = (
            f"Serper image search failed ({response.status_code}) for query '{query}'."
        )
        if error_text:
            detail = f"{detail} Response: {error_text[:300]}"
        raise RuntimeError(detail) from exc
    results = response.json().get("images", [])
    cache.set("images", cache_key, results)
    return results


def _search_images_with_client(config, cache, query):
    """Search for images using Serper.dev (wrapper for clarity)."""
    return _search_images(config, cache, query)


def _download_image(config, url, output_dir):
    """Download an image from URL (legacy function).

    Args:
        config: Pipeline configuration
        url: Image URL
        output_dir: Directory to save image

    Returns:
        Path to downloaded image
    """
    file_name = _filename_from_url(url, prefix="img")
    path = output_dir / file_name
    if path.exists():
        return path

    response = requests.get(
        url,
        timeout=config["request_timeout_seconds"],
        headers={"User-Agent": "Narrate-AI/1.0"},
    )
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "image" not in content_type:
        raise ValueError(f"URL did not return an image: {url}")
    path.write_bytes(response.content)
    return path


def _filename_from_url(url, prefix):
    """Generate safe filename from URL.

    Args:
        url: Image URL
        prefix: Prefix for filename (e.g., "img")

    Returns:
        Safe filename with prefix
    """
    parsed = urlparse(url)
    stem = Path(parsed.path).name or "image.jpg"
    safe_stem = safe_filename(stem, max_length=100)
    if "." not in safe_stem:
        safe_stem = f"{safe_stem}.jpg"
    return f"{prefix}_{safe_stem}"
