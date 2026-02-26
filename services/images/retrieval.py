"""Image retrieval agent."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests

from core.cache import MultiLayerCache
from core.models import create_image_candidate
from core.text_utils import safe_filename


SERPERS_IMAGES_URL = "https://google.serper.dev/images"

MAX_IMAGE_DOWNLOAD_WORKERS = 8


def retrieve_images(config, cache, segments, images_root):
    """Retrieve images for script segments."""
    print(
        f"[IMAGES] Retrieving images for {len(segments)} segments",
        flush=True,
    )
    images_root.mkdir(parents=True, exist_ok=True)
    seen_urls = set()

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
    """Download a single image. Returns candidate dict or None on failure."""
    file_name = _filename_from_url(url, prefix="img")
    path = segment_dir / file_name

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
            timeout=(3, 10),
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
    """Search for images using Serper.dev."""
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
    """Search for images using Serper.dev."""
    return _search_images(config, cache, query)


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
