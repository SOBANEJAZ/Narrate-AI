"""Documentary pipeline using functional programming style."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .agents import (
    build_narrative_plan,
    build_segments,
    crawl_and_build_notes,
    create_ranking_state,
    discover_sources,
    enrich_segments,
    generate_section_queries,
    rank_images,
    retrieve_images,
    synthesize_audio,
    write_script,
)
from .cache import MultiLayerCache
from .config import get_resolution
from .llm import create_llm_client
from .models import create_script_segment, create_timeline_item
from .rag import create_pinecone_manager
from .text_utils import slugify
from .video import assemble_video, build_timeline

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None
    ImageDraw = None


class PipelineResult(dict):
    """Pipeline result as a dictionary with property accessors."""

    @property
    def topic(self):
        return self["topic"]

    @property
    def run_dir(self):
        return self["run_dir"]

    @property
    def script_path(self):
        return self["script_path"]

    @property
    def timeline_path(self):
        return self["timeline_path"]

    @property
    def manifest_path(self):
        return self["manifest_path"]

    @property
    def final_video_path(self):
        return self["final_video_path"]


def run_pipeline(config, topic):
    """Run the documentary generation pipeline."""
    print(f"[PIPELINE] Starting documentary generation for topic: {topic}", flush=True)
    run_dir = _create_run_dir(config, topic)
    print(f"[PIPELINE] Run directory: {run_dir}", flush=True)
    cache = MultiLayerCache(run_dir / config["cache_dir_name"])
    llm_client = create_llm_client(config)

    print("[PIPELINE] Step 1: Narrative planning", flush=True)
    plan = build_narrative_plan(llm_client, topic)

    print("[PIPELINE] Step 2: Research discovery", flush=True)
    sources = discover_sources(config, cache, topic)

    print("[PIPELINE] Step 3: Research notes", flush=True)
    notes = crawl_and_build_notes(config, cache, sources)

    print("[PIPELINE] Step 3.5: Indexing notes to Pinecone", flush=True)
    namespace = slugify(topic)[:50]
    pinecone_manager = create_pinecone_manager(config)
    if pinecone_manager:
        pinecone_manager.create_index_if_not_exists(namespace)
        pinecone_manager.index_notes(namespace, notes, topic)
        print(
            f"[PIPELINE] Notes indexed to Pinecone namespace: {namespace}", flush=True
        )
    else:
        print("[PIPELINE] Pinecone not available, using notes directly", flush=True)

    print("[PIPELINE] Step 4: Generating section queries for RAG", flush=True)
    section_queries = generate_section_queries(llm_client, plan)

    print(f"[RAG] Semantic search queries generated:", flush=True)
    for sq in section_queries.queries:
        print(f"  - Section: {sq.section_title} | Query: {sq.search_query}", flush=True)

    print("[PIPELINE] Step 5: Retrieving relevant notes from vector DB", flush=True)
    all_retrieved_notes = []
    if pinecone_manager:
        for sq in section_queries.queries:
            retrieved = pinecone_manager.retrieve_notes(
                namespace=namespace,
                query=sq.search_query,
                topic=topic,
                top_k=3,
            )
            all_retrieved_notes.extend(retrieved)
    else:
        all_retrieved_notes = notes[:15]

    print(f"[PIPELINE] Retrieved {len(all_retrieved_notes)} relevant notes", flush=True)

    print("[PIPELINE] Step 6: Script generation", flush=True)
    script = write_script(llm_client, topic, plan, all_retrieved_notes)

    script_path = run_dir / "script.txt"
    script_path.write_text(script, encoding="utf-8")
    _write_json(run_dir / "narrative_plan.json", plan.model_dump())
    _write_json(run_dir / "sources.json", sources)
    _write_json(run_dir / "notes.json", notes)
    _write_json(run_dir / "retrieved_notes.json", all_retrieved_notes)
    print(f"[PIPELINE] Script saved: {script_path}", flush=True)

    print("[PIPELINE] Step 7: Image placement segmentation", flush=True)
    segments = build_segments(script, config["sentence_span_per_segment"])
    if not segments:
        segments = [
            create_script_segment(
                segment_id=1,
                text=script,
                start_sentence=1,
                end_sentence=1,
            )
        ]
        print(
            "[PIPELINE] Script segmentation was empty; using single fallback segment",
            flush=True,
        )

    print("[PIPELINE] Step 8: Visual intelligence prompts", flush=True)
    segments = enrich_segments(
        llm_client,
        topic,
        segments,
        config["max_queries_per_segment"],
    )

    print("[PIPELINE] Step 9: Image retrieval", flush=True)
    segments = retrieve_images(config, cache, segments, run_dir / "images")

    print("[PIPELINE] Step 10: Image ranking", flush=True)
    ranking_state = create_ranking_state()
    segments = rank_images(ranking_state, segments)

    placeholder_count = _ensure_images_for_segments(
        config, segments, run_dir / "placeholders"
    )
    print(
        f"[PIPELINE] Image fallback placeholders used: {placeholder_count}", flush=True
    )

    print("[PIPELINE] Step 11: Narration generation", flush=True)
    segments = synthesize_audio(
        config,
        segments,
        run_dir / "audio",
        config.get("tts_provider", "elevenlabs"),
    )

    print("[PIPELINE] Step 12: Timeline synchronization", flush=True)
    timeline = build_timeline(segments)
    if not timeline:
        raise RuntimeError(
            "No timeline entries were produced. Cannot create final video."
        )
    total_duration = sum(item["duration_seconds"] for item in timeline)
    print(
        f"[PIPELINE] Timeline ready: {len(timeline)} items, total duration {total_duration:.2f}s",
        flush=True,
    )

    timeline_path = run_dir / "timeline.json"
    _write_json(timeline_path, timeline)
    final_video_path = run_dir / "final_output.mp4"
    print("[PIPELINE] Step 13: Video assembly", flush=True)
    assemble_video(
        timeline,
        final_video_path,
        resolution=get_resolution(config),
        fps=config["fps"],
        transition_seconds=config["transition_seconds"],
        zoom_strength=config["zoom_strength"],
        background_mode=config["background_mode"],
    )

    manifest_path = run_dir / "manifest.json"
    _write_json(
        manifest_path,
        {
            "topic": topic,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "plan": plan.model_dump(),
            "segment_count": len(segments),
            "segments": [_segment_manifest_entry(segment) for segment in segments],
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


def _create_run_dir(config, topic):
    """Create a run directory for the documentary."""
    now = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dir_name = f"{now}-{slugify(topic)[:60]}"
    run_dir = config["run_root"] / dir_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_json(path, payload):
    """Write JSON data to a file."""
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, default=str),
        encoding="utf-8",
    )


def _ensure_images_for_segments(config, segments, output_dir):
    """Ensure all segments have images, creating placeholders if needed."""
    output_dir.mkdir(parents=True, exist_ok=True)
    placeholder_count = 0
    for segment in segments:
        selected = segment.get("selected_image_path")
        if selected and selected.exists():
            continue

        candidates = segment.get("candidate_images", [])
        for candidate in candidates:
            local_path = candidate.get("local_path")
            if local_path and local_path.exists():
                segment["selected_image_path"] = local_path
                break

        selected = segment.get("selected_image_path")
        if selected and selected.exists():
            continue

        segment["selected_image_path"] = _make_placeholder_image(
            config,
            output_dir / f"segment_{segment['segment_id']:03d}.jpg",
            text=segment["text"],
        )
        placeholder_count += 1
        print(
            f"[PIPELINE] Segment {segment['segment_id']}: created placeholder image",
            flush=True,
        )
    return placeholder_count


def _make_placeholder_image(config, output_path, text):
    """Create a placeholder image with text."""
    if Image is None or ImageDraw is None:
        raise RuntimeError(
            "Pillow is required for fallback placeholder image generation."
        )

    width, height = get_resolution(config)
    image = Image.new("RGB", (width, height), color=(15, 18, 23))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, width - 40, height - 40), outline=(95, 105, 122), width=2)
    snippet = text.strip().replace("\n", " ")[:320]
    wrapped = _wrap_text(snippet, 52)
    draw.text((70, 90), "Narrate-AI Placeholder Visual", fill=(220, 220, 220))
    draw.text((70, 150), wrapped, fill=(200, 200, 200))
    image.save(output_path, format="JPEG", quality=90)
    return output_path


def _wrap_text(text, max_chars_per_line):
    """Wrap text to fit within a character limit per line."""
    words = text.split()
    lines = []
    current = []
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


def _segment_manifest_entry(segment):
    """Create a manifest entry for a segment."""
    return {
        "segment_id": segment["segment_id"],
        "text": segment["text"],
        "text_range": f"Sentence {segment['start_sentence']}-{segment['end_sentence']}",
        "search_queries": segment.get("search_queries", []),
        "visual_description": segment.get("visual_description", ""),
        "image_candidates": segment.get("candidate_images", []),
        "selected_image_path": str(segment.get("selected_image_path"))
        if segment.get("selected_image_path")
        else None,
        "narration_audio_path": str(segment.get("narration_audio_path"))
        if segment.get("narration_audio_path")
        else None,
        "duration_seconds": segment.get("duration_seconds", 0.0),
    }
