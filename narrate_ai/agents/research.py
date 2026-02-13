from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from ..cache import MultiLayerCache
from ..config import PipelineConfig
from ..models import ResearchNote, ResearchSource
from ..text_utils import chunk_text

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency fallback
    BeautifulSoup = None  # type: ignore[assignment]

try:
    from ddgs import DDGS
except Exception:  # pragma: no cover - optional dependency fallback
    DDGS = None  # type: ignore[assignment]

try:
    from crawl4ai import AsyncWebCrawler
except Exception:  # pragma: no cover - optional dependency fallback
    AsyncWebCrawler = None  # type: ignore[assignment]


AUTHORITATIVE_HINTS = (
    ".gov",
    ".edu",
    "britannica.com",
    "history.com",
    "nationalgeographic.com",
    "wikipedia.org",
)


@dataclass(slots=True)
class ResearchPipeline:
    config: PipelineConfig
    cache: MultiLayerCache

    def discover_sources(self, topic: str) -> list[ResearchSource]:
        print(f"[RESEARCH] Discovering sources for topic: {topic}", flush=True)
        cache_key = f"sources::{topic.lower()}"
        cached = self.cache.get("research", cache_key)
        if isinstance(cached, list) and cached:
            print(f"[RESEARCH] Using cached source list ({len(cached)} sources)", flush=True)
            return [
                ResearchSource(url=item["url"], title=item["title"], snippet=item.get("snippet", ""))
                for item in cached
            ]

        query = f"{topic} history timeline facts"
        sources: list[ResearchSource] = []

        if DDGS is not None:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=self.config.max_websites * 4))
                print(f"[RESEARCH] DDGS returned {len(results)} candidate links", flush=True)
                for item in results:
                    url = str(item.get("href") or item.get("url") or "").strip()
                    if not url:
                        continue
                    title = str(item.get("title", "")).strip() or url
                    snippet = str(item.get("body", "")).strip()
                    sources.append(ResearchSource(url=url, title=title, snippet=snippet))
            except Exception:
                print("[RESEARCH] DDGS lookup failed; using fallback sources", flush=True)
                pass

        if not sources:
            print("[RESEARCH] No web sources found; using fallback static sources", flush=True)
            sources = [
                ResearchSource(
                    url=f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}",
                    title=f"{topic} - Wikipedia",
                ),
                ResearchSource(
                    url=f"https://www.britannica.com/search?query={topic.replace(' ', '+')}",
                    title=f"{topic} - Britannica Search",
                ),
            ]

        deduped: dict[str, ResearchSource] = {}
        for source in sources:
            deduped[source.url] = source

        ranked = sorted(deduped.values(), key=self._source_score, reverse=True)
        selected = ranked[: self.config.max_websites]
        self.cache.set(
            "research",
            cache_key,
            [{"url": item.url, "title": item.title, "snippet": item.snippet} for item in selected],
        )
        print(f"[RESEARCH] Selected top {len(selected)} sources", flush=True)
        return selected

    def crawl_and_build_notes(self, sources: list[ResearchSource]) -> list[ResearchNote]:
        print(f"[RESEARCH] Crawling {len(sources)} sources and building notes", flush=True)
        notes: list[ResearchNote] = []
        for source in sources:
            print(f"[RESEARCH] Crawling: {source.url}", flush=True)
            raw = self._crawl_url(source.url)
            if not raw:
                print(f"[RESEARCH] No content extracted for: {source.url}", flush=True)
                continue
            source_note_count = 0
            for index, chunk in enumerate(chunk_text(raw, chunk_size_words=170, overlap_words=25), start=1):
                notes.append(ResearchNote(source_url=source.url, chunk_id=index, text=chunk))
                source_note_count += 1
                if index >= 4:
                    break
            print(
                f"[RESEARCH] Built {source_note_count} notes from {source.url}",
                flush=True,
            )
        print(f"[RESEARCH] Total notes built: {len(notes)}", flush=True)
        return notes

    def _source_score(self, source: ResearchSource) -> int:
        parsed = urlparse(source.url)
        domain = parsed.netloc.lower()
        score = 0
        if any(hint in domain for hint in AUTHORITATIVE_HINTS):
            score += 10
        score += min(len(source.snippet) // 40, 5)
        if domain.startswith("www."):
            score += 1
        return score

    def _crawl_url(self, url: str) -> str:
        cache_key = f"page::{url}"
        cached = self.cache.get("crawl", cache_key)
        if isinstance(cached, dict) and cached.get("text"):
            print(f"[RESEARCH] Using cached crawl for: {url}", flush=True)
            return str(cached["text"])

        text = ""
        if AsyncWebCrawler is not None:
            print(f"[RESEARCH] Trying crawl4ai for: {url}", flush=True)
            text = self._crawl_with_crawl4ai(url)
        if not text:
            print(f"[RESEARCH] Falling back to requests crawl for: {url}", flush=True)
            text = self._crawl_with_requests(url)
        if not text:
            text = f"Background note: no direct crawl output was available for {url}."
            print(f"[RESEARCH] Crawl failed for: {url}; using placeholder note", flush=True)

        self.cache.set("crawl", cache_key, {"text": text})
        return text

    def _crawl_with_crawl4ai(self, url: str) -> str:
        async def _run() -> str:
            async with AsyncWebCrawler() as crawler:  # type: ignore[misc]
                result = await crawler.arun(url=url)
                markdown = getattr(result, "markdown", "") or ""
                cleaned = getattr(result, "cleaned_html", "") or ""
                return str(markdown or cleaned)

        try:
            return asyncio.run(_run())
        except Exception:
            return ""

    def _crawl_with_requests(self, url: str) -> str:
        try:
            response = requests.get(
                url,
                timeout=self.config.request_timeout_seconds,
                headers={"User-Agent": "Narrate-AI/1.0"},
            )
            response.raise_for_status()
            html = response.text
        except Exception:
            return ""

        if BeautifulSoup is None:
            cleaned = re.sub(r"<[^>]+>", " ", html)
            return re.sub(r"\s+", " ", cleaned).strip()

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return re.sub(r"\s+", " ", soup.get_text(" ")).strip()
