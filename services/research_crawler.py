"""Research Service: Web crawling and source discovery.

This module handles:
1. Source discovery - Finding authoritative web sources using Serper.dev
2. Content crawling - Extracting text from discovered URLs using crawl4ai
3. Note creation - Chunking content into research notes for RAG

External APIs:
- Serper.dev: Google search API for finding sources
- crawl4ai: Async web crawler for extracting content
"""

import asyncio
import json
import re
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

import requests
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

from core.models import create_research_note, create_research_source


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


SERPER_SEARCH_URL = "https://google.serper.dev/search"

# Research note chunking settings
CHUNK_SIZE_WORDS = 400  # Words per chunk
CHUNK_OVERLAP_WORDS = 100  # Overlap between chunks
MAX_CHUNKS_PER_SOURCE = 4  # Limit chunks per source

# Source scoring weights
SCORE_AUTHORITATIVE_DOMAIN = 10
SCORE_MAX_SNIPPET = 5
SCORE_WWW_PREFIX = 1
SNIPPET_LENGTH_DIVISOR = 40  # Points per 40 chars of snippet


def chunk_text(
    text: str, chunk_size_words: int = 180, overlap_words: int = 30
) -> list[str]:
    """Split text into overlapping chunks of words.

    Used for preparing text for RAG indexing. The overlap ensures
    context is preserved at chunk boundaries.

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


# Domains that indicate authoritative/trustworthy sources
# Used to prioritize .edu, .gov, Wikipedia, major news, etc.
AUTHORITATIVE_HINTS = (
    ".gov",
    ".edu",
    "wikipedia.org",
    "britannica.com",
    "britannica.org",
    "history.com",
    "nationalgeographic.com",
    "bbc.com",
    "bbc.co.uk",
    "reuters.com",
    "aljazeera.com",
    "aljazeera.net",
    "jstor.org",
    "loc.gov",
    "si.edu",
    "metmuseum.org",
    "britishmuseum.org",
    "cia.gov",
    "worldbank.org",
    "un.org",
    "nasa.gov",
    "esa.int",
)


def discover_sources(config, cache, topic):
    """Discover authoritative web sources for a given topic.

    Uses Serper.dev Google Search API to find sources, then prioritizes
    authoritative sources (.edu, .gov, Wikipedia, major news outlets).

    Caching: Results are cached to avoid redundant API calls.

    Args:
        config: Pipeline configuration with API keys
        cache: MultiLayerCache for storing results
        topic: Documentary topic string

    Returns:
        List of research source dicts with url, title, snippet

    Raises:
        RuntimeError: If no sources found or API key missing
    """
    print(f"[RESEARCH] Discovering sources for topic: {topic}", flush=True)
    cache_key = f"sources::{topic.lower()}"
    cached = cache.get("research", cache_key)
    if isinstance(cached, list) and cached:
        print(
            f"[RESEARCH] Using cached source list ({len(cached)} sources)", flush=True
        )
        return [
            create_research_source(
                url=item["url"],
                title=item["title"],
                snippet=item.get("snippet", ""),
            )
            for item in cached
        ]

    # Build search query optimized for finding factual sources
    query = f"{topic} history timeline facts"
    sources = []

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
        SERPER_SEARCH_URL,
        headers=headers,
        json=payload,
        timeout=config["request_timeout_seconds"],
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        error_text = response.text.strip()
        detail = (
            f"Serper web search failed ({response.status_code}) for query '{query}'."
        )
        if error_text:
            detail = f"{detail} Response: {error_text[:300]}"
        raise RuntimeError(detail) from exc
    results = response.json().get("organic", [])
    print(f"[RESEARCH] Serper.dev returned {len(results)} candidate links", flush=True)
    for item in results:
        url = str(item.get("link") or item.get("url") or "").strip()
        if not url:
            continue
        title = str(item.get("title", "")).strip() or url
        snippet = str(item.get("snippet", "")).strip()
        sources.append(create_research_source(url=url, title=title, snippet=snippet))

    if not sources:
        raise RuntimeError(f"No web sources found for topic: {topic}")

    # Deduplicate by URL
    deduped = {}
    for source in sources:
        deduped[source["url"]] = source

    ranked = sorted(deduped.values(), key=_source_score, reverse=True)

    # Separate authoritative from non-authoritative
    authoritative = [s for s in ranked if _is_authoritative(s)]
    non_authoritative = [s for s in ranked if not _is_authoritative(s)]

    # Prefer authoritative sources, but have fallback
    if authoritative:
        selected = authoritative[: config["max_websites"]]
        print(
            f"[RESEARCH] Selected {len(selected)} authoritative sources (filtered from {len(ranked)} total)",
            flush=True,
        )
    else:
        selected = ranked[: config["max_websites"]]
        print(
            f"[RESEARCH] No authoritative sources found. Using {len(selected)} fallback sources from Serper.dev",
            flush=True,
        )
    cache.set(
        "research",
        cache_key,
        [
            {
                "url": item["url"],
                "title": item["title"],
                "snippet": item.get("snippet", ""),
            }
            for item in selected
        ],
    )
    print(f"[RESEARCH] Selected top {len(selected)} sources", flush=True)
    return selected


def crawl_and_build_notes(config, cache, sources):
    """Crawl sources and build research notes.

    For each source URL:
    1. Crawl the page content using crawl4ai
    2. Chunk into ~400 word segments with 100 word overlap
    3. Create research notes with source attribution

    Each note becomes a candidate for RAG retrieval.

    Args:
        config: Pipeline configuration
        cache: Cache for storing crawled content
        sources: List of source dicts from discover_sources

    Returns:
        List of research note dicts with source_url and text
    """
    print(f"[RESEARCH] Crawling {len(sources)} sources and building notes", flush=True)
    notes = []
    for source in sources:
        print(f"[RESEARCH] Crawling: {source['url']}", flush=True)
        raw = _crawl_url(config, cache, source["url"])
        if not raw:
            print(f"[RESEARCH] No content extracted for: {source['url']}", flush=True)
            continue
        # Create chunks from crawled content
        source_note_count = 0
        for index, chunk in enumerate(
            chunk_text(
                raw,
                chunk_size_words=CHUNK_SIZE_WORDS,
                overlap_words=CHUNK_OVERLAP_WORDS,
            ),
            start=1,
        ):
            notes.append(
                create_research_note(
                    source_url=source["url"],
                    text=chunk,
                )
            )
            source_note_count += 1
            if index >= MAX_CHUNKS_PER_SOURCE:
                break
        print(
            f"[RESEARCH] Built {source_note_count} notes from {source['url']}",
            flush=True,
        )
    print(f"[RESEARCH] Total notes built: {len(notes)}", flush=True)
    return notes


def _is_authoritative(source):
    """Check if source URL matches authoritative domain hints.

    Args:
        source: Source dict with 'url' key

    Returns:
        True if domain appears in AUTHORITATIVE_HINTS
    """
    parsed = urlparse(source["url"])
    domain = parsed.netloc.lower()
    return any(hint in domain for hint in AUTHORITATIVE_HINTS)


def _source_score(source):
    """Calculate authority score for ranking sources.

    Scoring factors:
    - Authoritative domain: +10 (from SCORE_AUTHORITATIVE_DOMAIN)
    - Longer snippet: +1 per 40 chars (from SNIPPET_LENGTH_DIVISOR)
    - www prefix: +1 (from SCORE_WWW_PREFIX)

    Args:
        source: Source dict

    Returns:
        Integer score (higher = more authoritative)
    """
    parsed = urlparse(source["url"])
    domain = parsed.netloc.lower()
    score = 0

    # Check for authoritative domain hints
    if any(hint in domain for hint in AUTHORITATIVE_HINTS):
        score += SCORE_AUTHORITATIVE_DOMAIN

    # Score based on snippet length
    snippet = source.get("snippet", "")
    score += min(len(snippet) // SNIPPET_LENGTH_DIVISOR, SCORE_MAX_SNIPPET)

    # Bonus for www prefix
    if domain.startswith("www."):
        score += SCORE_WWW_PREFIX

    return score


def _crawl_url(config, cache, url):
    """Crawl a URL and return extracted text content.

    Uses cache to avoid re-crawling same URL.

    Args:
        config: Pipeline configuration
        cache: Cache instance
        url: URL to crawl

    Returns:
        Extracted text content (or empty string if failed)
    """
    cache_key = f"page::{url}"
    cached = cache.get("crawl", cache_key)
    if isinstance(cached, dict) and cached.get("text"):
        print(f"[RESEARCH] Using cached crawl for: {url}", flush=True)
        return str(cached["text"])

    print(f"[RESEARCH] Crawling: {url}", flush=True)
    text = _crawl_with_crawl4ai(url)

    cache.set("crawl", cache_key, {"text": text})
    return text


def _crawl_with_crawl4ai(url):
    """Crawl URL using crawl4ai async web crawler.

    Extracts markdown or cleaned HTML from the page.

    Args:
        url: URL to crawl

    Returns:
        Extracted text content as string
    """

    async def _run():
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            markdown = getattr(result, "markdown", "") or ""
            cleaned = getattr(result, "cleaned_html", "") or ""
            return str(markdown or cleaned)

    return asyncio.run(_run())
