from __future__ import annotations

import argparse
from pathlib import Path

from narrate_ai import DocumentaryPipeline, PipelineConfig


def build_parser() -> argparse.ArgumentParser:
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
    return parser


def main() -> int:
    args = build_parser().parse_args()

    config = PipelineConfig.from_env()
    config.run_root = args.run_root
    config.background_mode = args.background
    config.max_websites = max(1, args.max_websites)
    config.max_queries_per_segment = max(1, args.max_queries)
    config.images_per_query = max(1, args.images_per_query)
    config.sentence_span_per_segment = max(1, args.sentence_span)
    print(
        "[CLI] Config:"
        f" run_root={config.run_root}"
        f", background={config.background_mode}"
        f", max_websites={config.max_websites}"
        f", max_queries={config.max_queries_per_segment}"
        f", images_per_query={config.images_per_query}"
        f", sentence_span={config.sentence_span_per_segment}",
        flush=True,
    )

    pipeline = DocumentaryPipeline(config)
    result = pipeline.run(args.topic)
    print(f"Run directory: {result.run_dir}")
    print(f"Script: {result.script_path}")
    print(f"Timeline: {result.timeline_path}")
    print(f"Manifest: {result.manifest_path}")
    print(f"Final video: {result.final_video_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
