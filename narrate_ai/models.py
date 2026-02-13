from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class NarrativeSection:
    title: str
    objective: str
    duration_seconds: int


@dataclass(slots=True)
class NarrativePlan:
    topic: str
    tone: str
    pacing: str
    target_duration_seconds: int
    sections: list[NarrativeSection]


@dataclass(slots=True)
class ResearchSource:
    url: str
    title: str
    snippet: str = ""


@dataclass(slots=True)
class ResearchNote:
    source_url: str
    chunk_id: int
    text: str


@dataclass(slots=True)
class ImageCandidate:
    url: str
    title: str
    source: str
    local_path: Path | None = None
    score: float = 0.0


@dataclass(slots=True)
class ScriptSegment:
    segment_id: int
    text: str
    start_sentence: int
    end_sentence: int
    search_queries: list[str] = field(default_factory=list)
    visual_description: str = ""
    candidate_images: list[ImageCandidate] = field(default_factory=list)
    selected_image_path: Path | None = None
    narration_audio_path: Path | None = None
    duration_seconds: float = 0.0


@dataclass(slots=True)
class TimelineItem:
    segment_id: int
    text: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    image_path: Path
    audio_path: Path
