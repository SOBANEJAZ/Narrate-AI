"""Image retrieval agent."""

from pathlib import Path
from urllib.parse import urlparse

import requests
from ddgs import DDGS

from ..core.cache import MultiLayerCache
from ..core.models import create_image_candidate
from ..core.text_utils import safe_filename


def retrieve_images(config, cache, segments, images_root):
    """Retrieve images for script segments."""
    print(
        f"[IMAGES] Retrieving images for {len(segments)} segments",
        flush=True,
    )
    images_root.mkdir(parents=True, exist_ok=True)
    seen_urls = set()

    for segment in segments:
        segment_dir = images_root / f"segment_{segment['segment_id']:03d}"
        segment_dir.mkdir(parents=True, exist_ok=True)
        print(
            f"[IMAGES] Segment {segment['segment_id']}: running {len(segment.get('search_queries', []))} queries",
            flush=True,
        )

        candidates = []
        queries = segment.get("search_queries", [])[: config["max_queries_per_segment"]]
        for query in queries:
            results = _search_images(config, cache, query, config["images_per_query"])
            print(
                f"[IMAGES] Segment {segment['segment_id']}: query '{query}' returned {len(results)} results",
                flush=True,
            )
            for item in results:
                image_url = str(item.get("image") or item.get("url") or "").strip()
                if not image_url or image_url in seen_urls:
                    continue
                seen_urls.add(image_url)
                title = str(item.get("title") or item.get("source") or "image").strip()
                source = str(item.get("source") or item.get("url") or "").strip()
                candidate = create_image_candidate(
                    url=image_url,
                    title=title,
                    source=source,
                )
                local_path = _download_image(config, candidate["url"], segment_dir)
                if local_path is not None:
                    candidate["local_path"] = local_path
                    candidates.append(candidate)
        segment["candidate_images"] = candidates
        print(
            f"[IMAGES] Segment {segment['segment_id']}: downloaded {len(candidates)} candidates",
            flush=True,
        )
    return segments


def _search_images(config, cache, query, max_results):
    """Search for images using DDGS."""
    cache_key = f"images::{query.lower()}::{max_results}"
    cached = cache.get("images", cache_key)
    if isinstance(cached, list):
        return [item for item in cached if isinstance(item, dict)]

    with DDGS() as ddgs:
        results = list(ddgs.images(query, max_results=max_results))
    cache.set("images", cache_key, results)
    return results


def _download_image(config, url, output_dir):
    """Download an image from URL."""
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
    """Generate safe filename from URL."""
    parsed = urlparse(url)
    stem = Path(parsed.path).name or "image.jpg"
    safe_stem = safe_filename(stem, max_length=100)
    if "." not in safe_stem:
        safe_stem = f"{safe_stem}.jpg"
    return f"{prefix}_{safe_stem}"
