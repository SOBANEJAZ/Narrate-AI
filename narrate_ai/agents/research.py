"""Research pipeline using functional programming style."""

import asyncio
import re
from urllib.parse import urlparse

import requests

from ..cache import MultiLayerCache
from ..models import create_research_note, create_research_source
from ..text_utils import chunk_text

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    from ddgs import DDGS
except Exception:
    DDGS = None

try:
    from crawl4ai import AsyncWebCrawler
except Exception:
    AsyncWebCrawler = None


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
    """Discover authoritative sources for the given topic."""
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

    query = f"{topic} history timeline facts"
    sources = []

    if DDGS is not None:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=config["max_websites"] * 4))
            print(
                f"[RESEARCH] DDGS returned {len(results)} candidate links", flush=True
            )
            for item in results:
                url = str(item.get("href") or item.get("url") or "").strip()
                if not url:
                    continue
                title = str(item.get("title", "")).strip() or url
                snippet = str(item.get("body", "")).strip()
                sources.append(
                    create_research_source(url=url, title=title, snippet=snippet)
                )
        except Exception:
            print("[RESEARCH] DDGS lookup failed; using fallback sources", flush=True)
            pass

    if not sources:
        print(
            "[RESEARCH] No web sources found; using fallback static sources", flush=True
        )
        sources = [
            create_research_source(
                url=f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}",
                title=f"{topic} - Wikipedia",
            ),
            create_research_source(
                url=f"https://www.britannica.com/search?query={topic.replace(' ', '+')}",
                title=f"{topic} - Britannica Search",
            ),
        ]

    deduped = {}
    for source in sources:
        deduped[source["url"]] = source

    ranked = sorted(deduped.values(), key=_source_score, reverse=True)

    authoritative = [s for s in ranked if _is_authoritative(s)]
    non_authoritative = [s for s in ranked if not _is_authoritative(s)]

    if authoritative:
        selected = authoritative[: config["max_websites"]]
        print(
            f"[RESEARCH] Selected {len(selected)} authoritative sources (filtered from {len(ranked)} total)",
            flush=True,
        )
    else:
        selected = ranked[: config["max_websites"]]
        print(
            f"[RESEARCH] No authoritative sources found. Using {len(selected)} fallback sources from DuckDuckGo",
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
    """Crawl sources and build research notes."""
    print(f"[RESEARCH] Crawling {len(sources)} sources and building notes", flush=True)
    notes = []
    for source in sources:
        print(f"[RESEARCH] Crawling: {source['url']}", flush=True)
        raw = _crawl_url(config, cache, source["url"])
        if not raw:
            print(f"[RESEARCH] No content extracted for: {source['url']}", flush=True)
            continue
        source_note_count = 0
        for index, chunk in enumerate(
            chunk_text(raw, chunk_size_words=170, overlap_words=25), start=1
        ):
            notes.append(
                create_research_note(
                    source_url=source["url"],
                    chunk_id=index,
                    text=chunk,
                )
            )
            source_note_count += 1
            if index >= 4:
                break
        print(
            f"[RESEARCH] Built {source_note_count} notes from {source['url']}",
            flush=True,
        )
    print(f"[RESEARCH] Total notes built: {len(notes)}", flush=True)
    return notes


def _is_authoritative(source):
    """Check if source matches authoritative hints."""
    parsed = urlparse(source["url"])
    domain = parsed.netloc.lower()
    return any(hint in domain for hint in AUTHORITATIVE_HINTS)


def _source_score(source):
    """Calculate authority score for a source."""
    parsed = urlparse(source["url"])
    domain = parsed.netloc.lower()
    score = 0
    if any(hint in domain for hint in AUTHORITATIVE_HINTS):
        score += 10
    snippet = source.get("snippet", "")
    score += min(len(snippet) // 40, 5)
    if domain.startswith("www."):
        score += 1
    return score


def _crawl_url(config, cache, url):
    """Crawl a URL and return text content."""
    cache_key = f"page::{url}"
    cached = cache.get("crawl", cache_key)
    if isinstance(cached, dict) and cached.get("text"):
        print(f"[RESEARCH] Using cached crawl for: {url}", flush=True)
        return str(cached["text"])

    text = ""
    if AsyncWebCrawler is not None:
        print(f"[RESEARCH] Trying crawl4ai for: {url}", flush=True)
        text = _crawl_with_crawl4ai(url)
    if not text:
        print(f"[RESEARCH] Falling back to requests crawl for: {url}", flush=True)
        text = _crawl_with_requests(config, url)
    if not text:
        text = f"Background note: no direct crawl output was available for {url}."
        print(f"[RESEARCH] Crawl failed for: {url}; using placeholder note", flush=True)

    cache.set("crawl", cache_key, {"text": text})
    return text


def _crawl_with_crawl4ai(url):
    """Crawl URL using crawl4ai."""

    async def _run():
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            markdown = getattr(result, "markdown", "") or ""
            cleaned = getattr(result, "cleaned_html", "") or ""
            return str(markdown or cleaned)

    try:
        return asyncio.run(_run())
    except Exception:
        return ""


def _crawl_with_requests(config, url):
    """Crawl URL using requests as fallback."""
    try:
        response = requests.get(
            url,
            timeout=config["request_timeout_seconds"],
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
