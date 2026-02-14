"""Model type definitions using TypedDict (functional programming style).

This module defines all data structures as TypedDict types instead of dataclasses,
allowing for a functional programming approach throughout the codebase.
"""

from __future__ import annotations

from pathlib import Path
from typing import NotRequired, TypedDict


class NarrativeSection(TypedDict):
    """A section within a narrative plan."""

    title: str
    objective: str
    duration_seconds: int


def create_narrative_section(
    title: str,
    objective: str,
    duration_seconds: int,
) -> NarrativeSection:
    """Create a NarrativeSection instance."""
    return {
        "title": title,
        "objective": objective,
        "duration_seconds": duration_seconds,
    }


class NarrativePlan(TypedDict):
    """Complete narrative plan for a documentary."""

    topic: str
    tone: str
    pacing: str
    target_duration_seconds: int
    sections: list[NarrativeSection]


def create_narrative_plan(
    topic: str,
    tone: str,
    pacing: str,
    target_duration_seconds: int,
    sections: list[NarrativeSection],
) -> NarrativePlan:
    """Create a NarrativePlan instance."""
    return {
        "topic": topic,
        "tone": tone,
        "pacing": pacing,
        "target_duration_seconds": target_duration_seconds,
        "sections": sections,
    }


class ResearchSource(TypedDict):
    """A source discovered during research."""

    url: str
    title: str
    snippet: NotRequired[str]


def create_research_source(
    url: str,
    title: str,
    snippet: str = "",
) -> ResearchSource:
    """Create a ResearchSource instance."""
    result: ResearchSource = {
        "url": url,
        "title": title,
    }
    if snippet:
        result["snippet"] = snippet
    return result


class ResearchNote(TypedDict):
    """A note extracted from a research source."""

    source_url: str
    chunk_id: int
    text: str


def create_research_note(
    source_url: str,
    chunk_id: int,
    text: str,
) -> ResearchNote:
    """Create a ResearchNote instance."""
    return {
        "source_url": source_url,
        "chunk_id": chunk_id,
        "text": text,
    }


class ImageCandidate(TypedDict):
    """A candidate image for a script segment."""

    url: str
    title: str
    source: str
    local_path: NotRequired[Path | None]
    score: NotRequired[float]


def create_image_candidate(
    url: str,
    title: str,
    source: str,
    local_path: Path | None = None,
    score: float = 0.0,
) -> ImageCandidate:
    """Create an ImageCandidate instance."""
    result: ImageCandidate = {
        "url": url,
        "title": title,
        "source": source,
    }
    if local_path is not None:
        result["local_path"] = local_path
    if score != 0.0:
        result["score"] = score
    return result


class ScriptSegment(TypedDict):
    """A segment of the script with associated metadata."""

    segment_id: int
    text: str
    start_sentence: int
    end_sentence: int
    search_queries: NotRequired[list[str]]
    visual_description: NotRequired[str]
    candidate_images: NotRequired[list[ImageCandidate]]
    selected_image_path: NotRequired[Path | None]
    narration_audio_path: NotRequired[Path | None]
    duration_seconds: NotRequired[float]


def create_script_segment(
    segment_id: int,
    text: str,
    start_sentence: int,
    end_sentence: int,
    search_queries: list[str] | None = None,
    visual_description: str = "",
    candidate_images: list[ImageCandidate] | None = None,
    selected_image_path: Path | None = None,
    narration_audio_path: Path | None = None,
    duration_seconds: float = 0.0,
) -> ScriptSegment:
    """Create a ScriptSegment instance."""
    result: ScriptSegment = {
        "segment_id": segment_id,
        "text": text,
        "start_sentence": start_sentence,
        "end_sentence": end_sentence,
    }
    if search_queries is not None:
        result["search_queries"] = search_queries
    if visual_description:
        result["visual_description"] = visual_description
    if candidate_images is not None:
        result["candidate_images"] = candidate_images
    if selected_image_path is not None:
        result["selected_image_path"] = selected_image_path
    if narration_audio_path is not None:
        result["narration_audio_path"] = narration_audio_path
    if duration_seconds != 0.0:
        result["duration_seconds"] = duration_seconds
    return result


class TimelineItem(TypedDict):
    """An item in the video timeline."""

    segment_id: int
    text: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    image_path: Path
    audio_path: Path


def create_timeline_item(
    segment_id: int,
    text: str,
    start_seconds: float,
    end_seconds: float,
    duration_seconds: float,
    image_path: Path,
    audio_path: Path,
) -> TimelineItem:
    """Create a TimelineItem instance."""
    return {
        "segment_id": segment_id,
        "text": text,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": duration_seconds,
        "image_path": image_path,
        "audio_path": audio_path,
    }
