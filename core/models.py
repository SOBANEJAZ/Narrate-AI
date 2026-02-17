"""Model type definitions using plain dictionaries.

This module defines all data structures as plain dictionary types instead of dataclasses.

Also provides Pydantic models for structured LLM outputs with better validation.
"""

from pathlib import Path

from pydantic import BaseModel


class NarrativeSection(BaseModel):
    """Pydantic model for narrative section."""

    title: str
    objective: str
    duration_seconds: int


class NarrativePlan(BaseModel):
    """Pydantic model for narrative plan."""

    topic: str
    tone: str
    pacing: str
    target_duration_seconds: int
    sections: list[NarrativeSection]


class VisualIntelligence(BaseModel):
    """Pydantic model for visual intelligence output."""

    search_queries: list[str]
    visual_description: str


class SectionQuery(BaseModel):
    """Pydantic model for section query in RAG."""

    section_title: str
    section_objective: str
    search_query: str


class PlanQueries(BaseModel):
    """Pydantic model for all section queries."""

    queries: list[SectionQuery]


class ResearchNote(BaseModel):
    """Pydantic model for research note with metadata."""

    source_url: str
    text: str
    score: float = 0.0


def create_narrative_section(title, objective, duration_seconds):
    """Create a NarrativeSection instance."""
    return {
        "title": title,
        "objective": objective,
        "duration_seconds": duration_seconds,
    }


def create_narrative_plan(topic, tone, pacing, target_duration_seconds, sections):
    """Create a NarrativePlan instance."""
    return {
        "topic": topic,
        "tone": tone,
        "pacing": pacing,
        "target_duration_seconds": target_duration_seconds,
        "sections": sections,
    }


def create_research_source(url, title, snippet=""):
    """Create a ResearchSource instance."""
    result = {
        "url": url,
        "title": title,
    }
    if snippet:
        result["snippet"] = snippet
    return result


def create_research_note(source_url, text):
    """Create a ResearchNote instance."""
    return {
        "source_url": source_url,
        "text": text,
    }


def create_image_candidate(url, title, source, local_path=None, score=0.0):
    """Create an ImageCandidate instance."""
    result = {
        "url": url,
        "title": title,
        "source": source,
    }
    if local_path is not None:
        result["local_path"] = local_path
    if score != 0.0:
        result["score"] = score
    return result


def create_script_segment(
    segment_id,
    text,
    start_sentence,
    end_sentence,
    search_queries=None,
    visual_description="",
    candidate_images=None,
    selected_image_path=None,
    narration_audio_path=None,
    duration_seconds=0.0,
):
    """Create a ScriptSegment instance."""
    result = {
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


def create_timeline_item(
    segment_id,
    text,
    start_seconds,
    end_seconds,
    duration_seconds,
    image_path,
    audio_path,
):
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
