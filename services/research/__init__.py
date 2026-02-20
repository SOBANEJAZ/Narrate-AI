"""Research service for web discovery and content crawling."""

from services.research.crawler import crawl_and_build_notes, discover_sources

__all__ = ["crawl_and_build_notes", "discover_sources"]
