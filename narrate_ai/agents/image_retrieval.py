from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from ..cache import MultiLayerCache
from ..config import PipelineConfig
from ..models import ImageCandidate, ScriptSegment
from ..text_utils import safe_filename

try:
    from ddgs import DDGS
except Exception:  # pragma: no cover - optional dependency fallback
    DDGS = None  # type: ignore[assignment]


@dataclass(slots=True)
class ImageRetrievalAgent:
    config: PipelineConfig
    cache: MultiLayerCache

    def retrieve(
        self, segments: list[ScriptSegment], images_root: Path
    ) -> list[ScriptSegment]:
        print(
            f"[IMAGES] Retrieving images for {len(segments)} segments",
            flush=True,
        )
        images_root.mkdir(parents=True, exist_ok=True)
        seen_urls: set[str] = set()

        for segment in segments:
            segment_dir = images_root / f"segment_{segment.segment_id:03d}"
            segment_dir.mkdir(parents=True, exist_ok=True)
            print(
                f"[IMAGES] Segment {segment.segment_id}: running {len(segment.search_queries)} queries",
                flush=True,
            )

            candidates: list[ImageCandidate] = []
            for query in segment.search_queries[: self.config.max_queries_per_segment]:
                results = self._search_images(query, self.config.images_per_query)
                print(
                    f"[IMAGES] Segment {segment.segment_id}: query '{query}' returned {len(results)} results",
                    flush=True,
                )
                for item in results:
                    image_url = str(item.get("image") or item.get("url") or "").strip()
                    if not image_url or image_url in seen_urls:
                        continue
                    seen_urls.add(image_url)
                    title = str(
                        item.get("title") or item.get("source") or "image"
                    ).strip()
                    source = str(item.get("source") or item.get("url") or "").strip()
                    candidate = ImageCandidate(
                        url=image_url, title=title, source=source
                    )
                    candidate.local_path = self._download_image(
                        candidate.url, segment_dir
                    )
                    if candidate.local_path is None:
                        continue
                    candidates.append(candidate)
            segment.candidate_images = candidates
            print(
                f"[IMAGES] Segment {segment.segment_id}: downloaded {len(candidates)} candidates",
                flush=True,
            )
        return segments

    def _search_images(self, query: str, max_results: int) -> list[dict]:
        cache_key = f"images::{query.lower()}::{max_results}"
        cached = self.cache.get("images", cache_key)
        if isinstance(cached, list):
            return [item for item in cached if isinstance(item, dict)]

        if DDGS is None:
            return []

        try:
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=max_results))
            self.cache.set("images", cache_key, results)
            return results
        except Exception:
            return []

    def _download_image(self, url: str, output_dir: Path) -> Path | None:
        file_name = self._filename_from_url(url, prefix="img")
        path = output_dir / file_name
        if path.exists():
            return path

        try:
            response = requests.get(
                url,
                timeout=self.config.request_timeout_seconds,
                headers={"User-Agent": "Narrate-AI/1.0"},
            )
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type:
                return None
            path.write_bytes(response.content)
            return path
        except Exception:
            return None

    @staticmethod
    def _filename_from_url(url: str, prefix: str) -> str:
        parsed = urlparse(url)
        stem = Path(parsed.path).name or "image.jpg"
        safe_stem = safe_filename(stem, max_length=100)
        if "." not in safe_stem:
            safe_stem = f"{safe_stem}.jpg"
        return f"{prefix}_{safe_stem}"
