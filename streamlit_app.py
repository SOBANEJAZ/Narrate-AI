"""Streamlit Web UI for Narrate-AI.

This module provides a web-based interface for generating documentaries.
It wraps the CLI with a user-friendly UI built using Streamlit.

Features:
- Topic input with examples
- Configuration options (background, max websites, max queries)
- TTS provider selection with availability checking
- Live log streaming during generation
- Video playback on completion

Run with:
    streamlit run streamlit_app.py
"""

import os
import shlex
import subprocess
import sys
from pathlib import Path

import streamlit as st


APP_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = APP_ROOT / "main.py"

DEFAULT_MAX_WEBSITES = 4
DEFAULT_TTS_PROVIDER = "elevenlabs"


def _build_command(
    topic,
    max_websites,
    tts_provider,
):
    """Build the CLI command for the pipeline.

    Args:
        topic: Documentary topic
        max_websites: Max websites to research
        tts_provider: TTS provider name

    Returns:
        List of command arguments
    """
    return [
        sys.executable,
        str(MAIN_SCRIPT),
        topic,
        "--max-websites",
        str(max_websites),
        "--tts-provider",
        tts_provider,
    ]


def _extract_value(logs, prefix):
    """Extract a value from log output lines.

    Looks for lines starting with "prefix: value" in reverse order
    (most recent first).

    Args:
        logs: List of log lines
        prefix: Prefix to search for (e.g., "Run directory:")

    Returns:
        Extracted value or None
    """
    for line in reversed(logs):
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def main():
    """Main Streamlit application.

    Displays UI, collects user inputs, runs the pipeline,
    and displays results including the final video.
    """
    st.set_page_config(page_title="Narrate-AI", layout="wide")
    st.title("Narrate-AI Documentary Generator")
    st.caption(
        "Transform any topic into a documentary video with AI narration and images."
    )

    # Show pipeline explanation
    st.info("""
    **How it works:** Enter a topic, and the AI will:
    1. Research the topic from authoritative sources
    2. Write a documentary script
    3. Find and rank relevant images
    4. Generate AI narration
    5. Assemble everything into a video
    """)

    # Configuration help section
    with st.expander("Configuration Options Help", expanded=False):
        st.markdown("""
        ### **--max-websites** `4`
        Maximum number of websites to crawl for research. The system searches Google/Serper.dev
        and picks the top authoritative sources (Wikipedia, .edu, .gov sites, etc.) to gather
        information for the script. More = better research but slower processing.

        ### **--tts-provider** `elevenlabs` or `edge_tts`
        Text-to-speech engine for narration:
        - **elevenlabs**: High-quality AI voices (requires ELEVENLABS_API_KEY)
        - **edge_tts**: Free Microsoft voices (lower quality, no API key needed)
        """)

    # Input section
    topic = st.text_input(
        "Topic",
        value="Apollo Program",
        help="Enter any historical topic, event, person, or concept you want a documentary about",
    )

    col1, col2 = st.columns(2)
    with col1:
        max_websites = st.number_input(
            "Max Websites",
            min_value=1,
            step=1,
            value=DEFAULT_MAX_WEBSITES,
            help="Number of websites to research (more = better script but slower)",
        )

    # TTS Provider section
    st.subheader("Text-to-Speech Provider")

    has_elevenlabs_key = bool(os.getenv("ELEVENLABS_API_KEY"))

    tts_provider = st.radio(
        "Select TTS Provider",
        options=["elevenlabs", "edge_tts"],
        index=0 if DEFAULT_TTS_PROVIDER == "elevenlabs" else 1,
        help="Voice synthesis: ElevenLabs (high quality, paid) or Edge TTS (free, lower quality)",
    )

    # Show warnings based on provider selection
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

    # Run button
    run_clicked = st.button(
        "Generate Documentary", type="primary", use_container_width=True
    )
    if not run_clicked:
        return

    # Validate input
    topic = topic.strip()
    if not topic:
        st.error("Topic is required.")
        return

    # Build and display command
    command = _build_command(
        topic=topic,
        max_websites=int(max_websites),
        tts_provider=tts_provider,
    )
    st.markdown("**Running command:**")
    st.code(" ".join(shlex.quote(part) for part in command), language="bash")

    # Run pipeline with live log streaming
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

    # Stream logs in real-time
    assert process.stdout is not None
    for line in process.stdout:
        logs.append(line.rstrip("\n"))
        log_box.code("\n".join(logs), language="text")

    # Check result
    return_code = process.wait()
    if return_code != 0:
        st.error(f"Pipeline failed with exit code {return_code}.")
        return

    st.success("Pipeline completed successfully.")

    # Extract and display output paths
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

    # Play video if available
    if final_video and Path(final_video).exists():
        st.video(str(final_video))


if __name__ == "__main__":
    main()
