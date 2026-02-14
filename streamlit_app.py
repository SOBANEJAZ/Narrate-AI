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
DEFAULT_MAX_WEBSITES = 4
DEFAULT_MAX_QUERIES = 5
DEFAULT_IMAGES_PER_QUERY = 5
DEFAULT_SENTENCE_SPAN = 3
DEFAULT_TTS_PROVIDER = "elevenlabs"


def _build_command(
    topic,
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
    st.caption(
        "Transform any topic into a documentary video with AI narration and images."
    )

    st.info("""
    **How it works:** Enter a topic, and the AI will:
    1. Research the topic from authoritative sources
    2. Write a documentary script
    3. Find and rank relevant images
    4. Generate AI narration
    5. Assemble everything into a video
    """)

    with st.expander("Configuration Options Help", expanded=False):
        st.markdown("""
        ### **--background** `black` or `blur`
        How images fill the screen when their aspect ratio doesn't match the video (16:9).
        - **black**: Puts black bars around images (letterboxing)
        - **blur**: Blurs and stretches the image to fill the entire screen
        
        ### **--max-websites** `4`
        Maximum number of websites to crawl for research. The system searches Google/DuckDuckGo 
        and picks the top authoritative sources (Wikipedia, .edu, .gov sites, etc.) to gather 
        information for the script. More = better research but slower processing.
        
        ### **--max-queries** `5`
        Maximum image search queries per video segment. Each segment generates up to 5 different 
        search queries to find relevant images. Higher = more image variety but slower processing.
        
        ### **--images-per-query** `5`
        Number of images to download per search query. If searching for "Apollo 11 landing", 
        it will download the top 5 images from that query.
        
        ### **--sentence-span** `3`
        How many sentences of the script are grouped together into one video segment. 
        - Lower (1-2): Faster image changes, more dynamic
        - Higher (4-5): Slower changes, more time per image
        
        ### **--tts-provider** `elevenlabs` or `edge_tts`
        Text-to-speech engine for narration:
        - **elevenlabs**: High-quality AI voices (requires ELEVENLABS_API_KEY)
        - **edge_tts**: Free Microsoft voices (lower quality, no API key needed)
        """)

    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input(
            "Topic",
            value="Apollo Program",
            help="Enter any historical topic, event, person, or concept you want a documentary about",
        )
        background = st.selectbox(
            "Background",
            options=["black", "blur"],
            index=0 if DEFAULT_BACKGROUND == "black" else 1,
            help="How to display images: black bars (letterbox) or blur-fill",
        )
    with col2:
        max_websites = st.number_input(
            "Max Websites",
            min_value=1,
            step=1,
            value=DEFAULT_MAX_WEBSITES,
            help="Number of websites to research (more = better script but slower)",
        )
        max_queries = st.number_input(
            "Max Queries",
            min_value=1,
            step=1,
            value=DEFAULT_MAX_QUERIES,
            help="Image search queries per video segment",
        )
        images_per_query = st.number_input(
            "Images Per Query",
            min_value=1,
            step=1,
            value=DEFAULT_IMAGES_PER_QUERY,
            help="Images to download per search query",
        )
        sentence_span = st.number_input(
            "Sentence Span",
            min_value=1,
            step=1,
            value=DEFAULT_SENTENCE_SPAN,
            help="Sentences grouped per video clip (lower = faster image changes)",
        )

    st.subheader("Text-to-Speech Provider")

    has_elevenlabs_key = bool(os.getenv("ELEVENLABS_API_KEY"))

    tts_provider = st.radio(
        "Select TTS Provider",
        options=["elevenlabs", "edge_tts"],
        index=0 if DEFAULT_TTS_PROVIDER == "elevenlabs" else 1,
        help="Voice synthesis: ElevenLabs (high quality, paid) or Edge TTS (free, lower quality)",
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
