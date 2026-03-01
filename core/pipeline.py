"""Documentary generation pipeline.

This is the main orchestration module that coordinates all pipeline steps
from research to final video output.

Pipeline Phases:
1. Research - Discover sources, crawl content, index to vector DB
2. Generation - Write script, segment for images
3. Retrieval - Find and rank images
4. Production - Synthesize audio, build timeline, render video

Each step produces intermediate output files for debugging.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from agents import (
    build_narrative_plan,
    build_segments,
    crawl_and_build_notes,
    create_ranking_state,
    discover_sources,
    generate_section_queries,
    rank_images,
    retrieve_images,
    segment_for_images,
    synthesize_audio,
    write_script,
)
from core.cache import MultiLayerCache
from core.config import get_resolution, get_groq_client, get_top_k
from core.models import create_script_segment, create_timeline_item
from core.text_utils import slugify
from services.rag import create_pinecone_manager
from services.video import assemble_video, build_timeline


class PipelineResult(dict):
    """Pipeline result with property accessors for convenient access.

    After pipeline completes, this provides easy access to:
    - run_dir: Directory with all output files
    - script_path: Generated narration script
    - timeline_path: Video timeline JSON
    - manifest_path: Complete run metadata
    - final_video_path: Final MP4 video
    """

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
    """Run the complete documentary generation pipeline.

    This is the main entry point for generating a documentary video.
    It orchestrates all phases from research to final video assembly.

    Pipeline Steps:
    1. Create run directory and cache
    2. Build narrative plan (outline with sections)
    3. Discover and crawl web sources
    4. Index research notes to Pinecone (RAG)
    5. Generate semantic search queries for each section
    6. Retrieve relevant notes using vector similarity
    7. Write narration script
    8. Segment script for image placement
    9. Retrieve candidate images for each segment
    10. Rank images using CLIP
    11. Synthesize audio narration
    12. Build timeline with synchronized audio/image
    13. Assemble final video

    Args:
        config: Pipeline configuration dict
        topic: Documentary topic string

    Returns:
        PipelineResult with paths to all output files

    Raises:
        RuntimeError: If any step fails
    """
    print(f"[PIPELINE] Starting documentary generation for topic: {topic}", flush=True)
    run_dir = _create_run_dir(config, topic)
    print(f"[PIPELINE] Run directory: {run_dir}", flush=True)
    cache = MultiLayerCache(run_dir / config["cache_dir_name"])

    # Initialize Groq client and create agent context
    # The context is passed to all agents so they can access LLM and config
    groq_client = get_groq_client(config["groq_api_key"])
    agent_context = {
        "groq_client": groq_client,
        "config": config,
    }

    # ========== PHASE 1: Research & Context Building ==========
    print("[PIPELINE] Step 1: Narrative planning", flush=True)
    plan = build_narrative_plan(agent_context, topic)

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
    section_queries = generate_section_queries(agent_context, plan)

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
                top_k=get_top_k(config),
            )
            all_retrieved_notes.extend(retrieved)
    else:
        # Fallback: use first 15 notes if Pinecone unavailable
        all_retrieved_notes = notes[:15]

    print(f"[PIPELINE] Retrieved {len(all_retrieved_notes)} relevant notes", flush=True)

    # Clean up Pinecone namespace to avoid accumulating data
    if pinecone_manager and namespace:
        pinecone_manager.clear_namespace(namespace)

    # ========== PHASE 2: Content Generation ==========
    print("[PIPELINE] Step 6: Script generation", flush=True)
    script = write_script(agent_context, topic, plan, all_retrieved_notes)

    # Save intermediate outputs for debugging
    script_path = run_dir / "script.txt"
    script_path.write_text(script, encoding="utf-8")
    _write_json(run_dir / "narrative_plan.json", plan.model_dump())
    _write_json(run_dir / "sources.json", sources)
    _write_json(run_dir / "notes.json", notes)
    _write_json(run_dir / "retrieved_notes.json", all_retrieved_notes)
    print(f"[PIPELINE] Script saved: {script_path}", flush=True)

    print("[PIPELINE] Step 6.5: Image segmentation", flush=True)
    segmentation = segment_for_images(agent_context, script)

    print("[PIPELINE] Step 7: Image placement segmentation", flush=True)
    segments = build_segments(script, segmentation)
    if not segments:
        # Fallback: single segment covering entire script
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

    # ========== PHASE 3: Image Retrieval ==========
    print("[PIPELINE] Step 8: Image retrieval", flush=True)
    segments = retrieve_images(config, cache, segments, run_dir / "images")

    print("[PIPELINE] Step 9: Image ranking", flush=True)
    ranking_state = create_ranking_state()
    segments = rank_images(ranking_state, segments)

    # Verify all segments got images
    for segment in segments:
        if not segment.get("selected_image_path"):
            raise RuntimeError(f"No image selected for segment {segment['segment_id']}")

    # ========== PHASE 4: Production ==========
    print("[PIPELINE] Step 9: Narration generation", flush=True)
    segments = synthesize_audio(
        config,
        segments,
        run_dir / "audio",
        config.get("tts_provider", "elevenlabs"),
    )

    print("[PIPELINE] Step 10: Timeline synchronization", flush=True)
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
    print("[PIPELINE] Step 11: Video assembly", flush=True)
    assemble_video(
        timeline,
        final_video_path,
        resolution=get_resolution(config),
        fps=config["fps"],
        transition_seconds=config["transition_seconds"],
        zoom_strength=config["zoom_strength"],
    )

    # Save complete manifest for debugging/reproducibility
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
    """Create a timestamped run directory for this documentary.

    Directory name format: YYYYMMDD-HHMMSS-topic-slug

    Args:
        config: Pipeline configuration
        topic: Documentary topic

    Returns:
        Path to created run directory
    """
    now = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dir_name = f"{now}-{slugify(topic)[:60]}"
    run_dir = config["run_root"] / dir_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_json(path, payload):
    """Write JSON data to a file with proper encoding.

    Args:
        path: Output file path
        payload: Python object to serialize as JSON
    """
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, default=str),
        encoding="utf-8",
    )


def _segment_manifest_entry(segment):
    """Create a manifest entry for a segment (for debugging/output).

    Args:
        segment: Segment dict with all data

    Returns:
        Dict with serializable segment data for manifest
    """
    return {
        "segment_id": segment["segment_id"],
        "text": segment["text"],
        "text_range": f"Sentence {segment['start_sentence']}-{segment['end_sentence']}",
        "search_queries": segment.get("search_queries", []),
        "image_candidates": segment.get("candidate_images", []),
        "selected_image_path": str(segment.get("selected_image_path"))
        if segment.get("selected_image_path")
        else None,
        "narration_audio_path": str(segment.get("narration_audio_path"))
        if segment.get("narration_audio_path")
        else None,
        "duration_seconds": segment.get("duration_seconds", 0.0),
    }
