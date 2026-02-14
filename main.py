"""CLI entry point for documentary generation."""

import argparse
from pathlib import Path

from narrate_ai import (
    create_config_from_env,
    get_resolution,
    run_pipeline,
    update_config,
)


def build_parser():
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate a slideshow-style documentary video from a single topic.",
    )
    parser.add_argument("topic", help="Documentary topic to generate.")
    parser.add_argument(
        "--run-root",
        type=Path,
        default=Path("runs"),
        help="Directory where run artifacts are written.",
    )
    parser.add_argument(
        "--background",
        choices=["black", "blur"],
        default="black",
        help="Background fill mode for non-matching image aspect ratios.",
    )
    parser.add_argument("--max-websites", type=int, default=4)
    parser.add_argument("--max-queries", type=int, default=5)
    parser.add_argument("--images-per-query", type=int, default=5)
    parser.add_argument("--sentence-span", type=int, default=3)
    parser.add_argument(
        "--tts-provider",
        choices=["elevenlabs", "edge_tts"],
        default="elevenlabs",
        help="TTS provider to use for narration (elevenlabs requires API key).",
    )
    return parser


def main():
    """Main entry point."""
    args = build_parser().parse_args()

    config = create_config_from_env()
    config = update_config(
        config,
        run_root=args.run_root,
        background_mode=args.background,
        max_websites=max(1, args.max_websites),
        max_queries_per_segment=max(1, args.max_queries),
        images_per_query=max(1, args.images_per_query),
        sentence_span_per_segment=max(1, args.sentence_span),
        tts_provider=args.tts_provider,
    )

    print(
        "[CLI] Config:"
        f" run_root={config['run_root']}"
        f", background={config['background_mode']}"
        f", max_websites={config['max_websites']}"
        f", max_queries={config['max_queries_per_segment']}"
        f", images_per_query={config['images_per_query']}"
        f", sentence_span={config['sentence_span_per_segment']}"
        f", tts_provider={config['tts_provider']}",
        flush=True,
    )

    result = run_pipeline(config, args.topic)
    print(f"Run directory: {result.run_dir}")
    print(f"Script: {result.script_path}")
    print(f"Timeline: {result.timeline_path}")
    print(f"Manifest: {result.manifest_path}")
    print(f"Final video: {result.final_video_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
