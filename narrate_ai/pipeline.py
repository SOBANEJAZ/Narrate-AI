from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .agents import (
    ImagePlacementAgent,
    ImageRankingAgent,
    ImageRetrievalAgent,
    NarrationAgent,
    NarrativeArchitectAgent,
    ResearchPipeline,
    ScriptWriterAgent,
    VisualIntelligenceAgent,
)
from .cache import MultiLayerCache
from .config import PipelineConfig
from .llm import LLMClient
from .models import ScriptSegment
from .text_utils import slugify
from .video import assemble_video, build_timeline

try:
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover - optional dependency fallback
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]


@dataclass(slots=True)
class PipelineResult:
    topic: str
    run_dir: Path
    script_path: Path
    timeline_path: Path
    manifest_path: Path
    final_video_path: Path


@dataclass(slots=True)
class DocumentaryPipeline:
    config: PipelineConfig

    def run(self, topic: str) -> PipelineResult:
        print(f"[PIPELINE] Starting documentary generation for topic: {topic}", flush=True)
        run_dir = self._create_run_dir(topic)
        print(f"[PIPELINE] Run directory: {run_dir}", flush=True)
        cache = MultiLayerCache(run_dir / self.config.cache_dir_name)
        llm_client = LLMClient(self.config)

        narrative_architect = NarrativeArchitectAgent(llm_client)
        research_pipeline = ResearchPipeline(self.config, cache)
        script_writer = ScriptWriterAgent(llm_client)
        image_placement = ImagePlacementAgent(self.config.sentence_span_per_segment)
        visual_intelligence = VisualIntelligenceAgent(llm_client, self.config.max_queries_per_segment)
        image_retrieval = ImageRetrievalAgent(self.config, cache)
        image_ranking = ImageRankingAgent()
        narration_agent = NarrationAgent(self.config)

        print("[PIPELINE] Step 1: Narrative planning", flush=True)
        plan = narrative_architect.build_plan(topic)
        print("[PIPELINE] Step 2: Research discovery", flush=True)
        sources = research_pipeline.discover_sources(topic)
        print("[PIPELINE] Step 3: Crawl and RAG notes", flush=True)
        notes = research_pipeline.crawl_and_build_notes(sources)
        print("[PIPELINE] Step 4: Script generation", flush=True)
        script = script_writer.write_script(topic, plan, notes)

        script_path = run_dir / "script.txt"
        script_path.write_text(script, encoding="utf-8")
        self._write_json(run_dir / "narrative_plan.json", asdict(plan))
        self._write_json(run_dir / "sources.json", [asdict(source) for source in sources])
        self._write_json(run_dir / "notes.json", [asdict(note) for note in notes])
        print(f"[PIPELINE] Script saved: {script_path}", flush=True)

        print("[PIPELINE] Step 5: Image placement segmentation", flush=True)
        segments = image_placement.build_segments(script)
        if not segments:
            segments = [
                ScriptSegment(
                    segment_id=1,
                    text=script,
                    start_sentence=1,
                    end_sentence=1,
                )
            ]
            print("[PIPELINE] Script segmentation was empty; using single fallback segment", flush=True)

        print("[PIPELINE] Step 6: Visual intelligence prompts", flush=True)
        segments = visual_intelligence.enrich_segments(topic, segments)
        print("[PIPELINE] Step 7: Image retrieval", flush=True)
        segments = image_retrieval.retrieve(segments, run_dir / "images")
        print("[PIPELINE] Step 8: Image ranking", flush=True)
        segments = image_ranking.rank(segments)
        placeholder_count = self._ensure_images_for_segments(segments, run_dir / "placeholders")
        print(f"[PIPELINE] Image fallback placeholders used: {placeholder_count}", flush=True)
        print("[PIPELINE] Step 9: Narration generation", flush=True)
        segments = narration_agent.synthesize(segments, run_dir / "audio")

        print("[PIPELINE] Step 10: Timeline synchronization", flush=True)
        timeline = build_timeline(segments)
        if not timeline:
            raise RuntimeError("No timeline entries were produced. Cannot create final video.")
        total_duration = sum(item.duration_seconds for item in timeline)
        print(
            f"[PIPELINE] Timeline ready: {len(timeline)} items, total duration {total_duration:.2f}s",
            flush=True,
        )

        timeline_path = run_dir / "timeline.json"
        self._write_json(timeline_path, [asdict(item) for item in timeline])
        final_video_path = run_dir / "final_output.mp4"
        print("[PIPELINE] Step 11: Video assembly", flush=True)
        assemble_video(
            timeline,
            final_video_path,
            resolution=self.config.resolution,
            fps=self.config.fps,
            transition_seconds=self.config.transition_seconds,
            zoom_strength=self.config.zoom_strength,
            background_mode=self.config.background_mode,
        )

        manifest_path = run_dir / "manifest.json"
        self._write_json(
            manifest_path,
            {
                "topic": topic,
                "created_at_utc": datetime.now(UTC).isoformat(),
                "plan": asdict(plan),
                "segment_count": len(segments),
                "segments": [self._segment_manifest_entry(segment) for segment in segments],
                "final_video_path": str(final_video_path),
            },
        )
        print(f"[PIPELINE] Manifest saved: {manifest_path}", flush=True)
        print(f"[PIPELINE] Completed successfully: {final_video_path}", flush=True)

        return PipelineResult(
            topic=topic,
            run_dir=run_dir,
            script_path=script_path,
            timeline_path=timeline_path,
            manifest_path=manifest_path,
            final_video_path=final_video_path,
        )

    def _create_run_dir(self, topic: str) -> Path:
        now = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        dir_name = f"{now}-{slugify(topic)[:60]}"
        run_dir = self.config.run_root / dir_name
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, default=str),
            encoding="utf-8",
        )

    def _ensure_images_for_segments(self, segments: list[ScriptSegment], output_dir: Path) -> int:
        output_dir.mkdir(parents=True, exist_ok=True)
        placeholder_count = 0
        for segment in segments:
            if segment.selected_image_path and segment.selected_image_path.exists():
                continue

            for candidate in segment.candidate_images:
                if candidate.local_path and candidate.local_path.exists():
                    segment.selected_image_path = candidate.local_path
                    break

            if segment.selected_image_path and segment.selected_image_path.exists():
                continue

            segment.selected_image_path = self._make_placeholder_image(
                output_dir / f"segment_{segment.segment_id:03d}.jpg",
                text=segment.text,
            )
            placeholder_count += 1
            print(
                f"[PIPELINE] Segment {segment.segment_id}: created placeholder image",
                flush=True,
            )
        return placeholder_count

    def _make_placeholder_image(self, output_path: Path, text: str) -> Path:
        if Image is None or ImageDraw is None:
            raise RuntimeError("Pillow is required for fallback placeholder image generation.")

        width, height = self.config.resolution
        image = Image.new("RGB", (width, height), color=(15, 18, 23))
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 40, width - 40, height - 40), outline=(95, 105, 122), width=2)
        snippet = text.strip().replace("\n", " ")[:320]
        wrapped = self._wrap_text(snippet, 52)
        draw.text((70, 90), "Narrate-AI Placeholder Visual", fill=(220, 220, 220))
        draw.text((70, 150), wrapped, fill=(200, 200, 200))
        image.save(output_path, format="JPEG", quality=90)
        return output_path

    @staticmethod
    def _wrap_text(text: str, max_chars_per_line: int) -> str:
        words = text.split()
        lines: list[str] = []
        current: list[str] = []
        current_len = 0
        for word in words:
            next_len = current_len + len(word) + (1 if current else 0)
            if next_len > max_chars_per_line and current:
                lines.append(" ".join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len = next_len
        if current:
            lines.append(" ".join(current))
        return "\n".join(lines)

    def _segment_manifest_entry(self, segment: ScriptSegment) -> dict[str, object]:
        return {
            "segment_id": segment.segment_id,
            "text": segment.text,
            "text_range": f"Sentence {segment.start_sentence}-{segment.end_sentence}",
            "search_queries": segment.search_queries,
            "visual_description": segment.visual_description,
            "image_candidates": [asdict(candidate) for candidate in segment.candidate_images],
            "selected_image_path": str(segment.selected_image_path) if segment.selected_image_path else None,
            "narration_audio_path": str(segment.narration_audio_path) if segment.narration_audio_path else None,
            "duration_seconds": segment.duration_seconds,
        }
