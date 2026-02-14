"""Streamlit UI for Narrate-AI with TTS provider selection."""

import os
import shlex
import subprocess
import sys
from pathlib import Path

import streamlit as st


APP_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = APP_ROOT / "main.py"

DEFAULT_BACKGROUND = "black"
DEFAULT_RUN_ROOT = "runs"
DEFAULT_MAX_WEBSITES = 4
DEFAULT_MAX_QUERIES = 5
DEFAULT_IMAGES_PER_QUERY = 5
DEFAULT_SENTENCE_SPAN = 3
DEFAULT_TTS_PROVIDER = "elevenlabs"


def _build_command(
    topic,
    run_root,
    background,
    max_websites,
    max_queries,
    images_per_query,
    sentence_span,
    tts_provider,
):
    """Build the command to run the pipeline."""
    return [
        sys.executable,
        str(MAIN_SCRIPT),
        topic,
        "--run-root",
        run_root,
        "--background",
        background,
        "--max-websites",
        str(max_websites),
        "--max-queries",
        str(max_queries),
        "--images-per-query",
        str(images_per_query),
        "--sentence-span",
        str(sentence_span),
        "--tts-provider",
        tts_provider,
    ]


def _extract_value(lines, prefix):
    """Extract a value from log lines."""
    for line in reversed(lines):
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def main():
    """Main Streamlit app."""
    st.set_page_config(page_title="Narrate-AI", layout="wide")
    st.title("Narrate-AI Documentary Generator")
    st.caption("Streamlit UI for running the documentary pipeline.")

    with st.expander("Default CLI Options", expanded=True):
        st.markdown(
            "- `--run-root`: `runs`\n"
            "- `--background`: `black`\n"
            "- `--max-websites`: `4`\n"
            "- `--max-queries`: `5`\n"
            "- `--images-per-query`: `5`\n"
            "- `--sentence-span`: `3`\n"
            "- `--tts-provider`: `elevenlabs`"
        )

    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("Topic", value="Apollo Program")
        run_root = st.text_input("Run Root", value=DEFAULT_RUN_ROOT)
        background = st.selectbox(
            "Background",
            options=["black", "blur"],
            index=0 if DEFAULT_BACKGROUND == "black" else 1,
        )
    with col2:
        max_websites = st.number_input(
            "Max Websites", min_value=1, step=1, value=DEFAULT_MAX_WEBSITES
        )
        max_queries = st.number_input(
            "Max Queries", min_value=1, step=1, value=DEFAULT_MAX_QUERIES
        )
        images_per_query = st.number_input(
            "Images Per Query",
            min_value=1,
            step=1,
            value=DEFAULT_IMAGES_PER_QUERY,
        )
        sentence_span = st.number_input(
            "Sentence Span", min_value=1, step=1, value=DEFAULT_SENTENCE_SPAN
        )

    st.subheader("Text-to-Speech Provider")

    has_elevenlabs_key = bool(os.getenv("ELEVENLABS_API_KEY"))

    tts_provider = st.radio(
        "Select TTS Provider",
        options=["elevenlabs", "edge_tts"],
        index=0 if DEFAULT_TTS_PROVIDER == "elevenlabs" else 1,
        help="ElevenLabs provides higher quality voices but requires an API key. Edge TTS is free but lower quality.",
    )

    if tts_provider == "elevenlabs" and not has_elevenlabs_key:
        st.warning(
            "⚠️ ElevenLabs API key not found in environment. "
            "Set ELEVENLABS_API_KEY environment variable or switch to Edge TTS. "
            "The pipeline will use fallback audio if ElevenLabs is unavailable."
        )

    if tts_provider == "edge_tts":
        st.info(
            "ℹ️ Edge TTS uses Microsoft's free text-to-speech service. "
            "No API key required, but quality is lower than ElevenLabs."
        )

    run_clicked = st.button(
        "Generate Documentary", type="primary", use_container_width=True
    )
    if not run_clicked:
        return

    topic = topic.strip()
    if not topic:
        st.error("Topic is required.")
        return

    command = _build_command(
        topic=topic,
        run_root=run_root.strip() or DEFAULT_RUN_ROOT,
        background=background,
        max_websites=int(max_websites),
        max_queries=int(max_queries),
        images_per_query=int(images_per_query),
        sentence_span=int(sentence_span),
        tts_provider=tts_provider,
    )
    st.markdown("**Running command:**")
    st.code(" ".join(shlex.quote(part) for part in command), language="bash")

    log_box = st.empty()
    logs = []
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        command,
        cwd=str(APP_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None
    for line in process.stdout:
        logs.append(line.rstrip("\n"))
        log_box.code("\n".join(logs[-250:]), language="text")

    return_code = process.wait()
    if return_code != 0:
        st.error(f"Pipeline failed with exit code {return_code}.")
        return

    st.success("Pipeline completed successfully.")

    run_dir = _extract_value(logs, "Run directory")
    script_path = _extract_value(logs, "Script")
    timeline_path = _extract_value(logs, "Timeline")
    manifest_path = _extract_value(logs, "Manifest")
    final_video = _extract_value(logs, "Final video")

    if run_dir:
        st.write(f"Run directory: `{run_dir}`")
    if script_path:
        st.write(f"Script: `{script_path}`")
    if timeline_path:
        st.write(f"Timeline: `{timeline_path}`")
    if manifest_path:
        st.write(f"Manifest: `{manifest_path}`")
    if final_video:
        st.write(f"Final video: `{final_video}`")

    if final_video and Path(final_video).exists():
        st.video(str(final_video))


if __name__ == "__main__":
    main()
