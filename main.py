"""CLI Entry Point for Narrate-AI.

This script provides a command-line interface for generating
documentary videos. It's the primary way to run the pipeline
programmatically or in scripts.

Usage:
    python main.py "Apollo Program"
    python main.py "World War II" --max-websites 6
    python main.py "Climate Change" --tts-provider edge_tts

Environment Variables:
    See .env.example for required API keys
"""

import argparse
from pathlib import Path

from core.config import create_config_from_env
from core.pipeline import run_pipeline


def build_parser():
    """Build and configure the argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Generate a slideshow-style documentary video from a single topic.",
    )
    parser.add_argument(
        "topic",
        help="Documentary topic to generate (e.g., 'Apollo Program', 'World War II')",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        default=Path("runs"),
        help="Directory where run artifacts are written.",
    )
    parser.add_argument(
        "--max-websites",
        type=int,
        default=4,
        help="Maximum number of websites to research",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=3,
        help="Image search queries per video segment",
    )
    parser.add_argument(
        "--tts-provider",
        choices=["elevenlabs", "edge_tts"],
        default="elevenlabs",
        help="TTS provider for narration (elevenlabs requires API key)",
    )
    return parser


def main():
    """Main CLI entry point.

    Parses arguments, builds config, and runs the pipeline.
    Returns 0 on success, non-zero on failure.
    """
    args = build_parser().parse_args()

    # Build configuration from defaults + environment + CLI args
    config = create_config_from_env()
    config = {
        **config,
        "run_root": args.run_root,
        "max_websites": max(1, args.max_websites),
        "max_queries_per_segment": max(1, args.max_queries),
        "tts_provider": args.tts_provider,
    }

    # Log configuration
    print(
        "[CLI] Config:"
        f" run_root={config['run_root']}"
        f", max_websites={config['max_websites']}"
        f", max_queries={config['max_queries_per_segment']}"
        f", tts_provider={config['tts_provider']}",
        flush=True,
    )

    # Run the documentary generation pipeline
    result = run_pipeline(config, args.topic)

    # Print output paths
    print(f"Run directory: {result.run_dir}")
    print(f"Script: {result.script_path}")
    print(f"Timeline: {result.timeline_path}")
    print(f"Manifest: {result.manifest_path}")
    print(f"Final video: {result.final_video_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
