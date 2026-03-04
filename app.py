"""Streamlit Web UI for Narrate-AI - Cinematic Documentary Studio

This module provides a cinematic web interface for generating documentaries.

"""

import os
import re
import subprocess
import sys
from html import escape
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


APP_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = APP_ROOT / "main.py"

DEFAULT_MAX_WEBSITES = 1
DEFAULT_TTS_PROVIDER = "elevenlabs"

PIPELINE_STAGES = [
    ("search", "Research"),
    ("file-text", "Script"),
    ("image", "Images"),
    ("volume-2", "Narration"),
    ("film", "Export"),
]

STEP_STAGE_BY_NUMBER = {
    1: 0,  # Narrative planning
    2: 0,  # Research discovery
    3: 0,  # Research notes
    4: 0,  # Pinecone indexing
    5: 0,  # Section queries
    6: 0,  # Vector retrieval
    7: 1,  # Script generation
    8: 1,  # Image segmentation
    9: 1,  # Image placement segmentation
    10: 2,  # Image retrieval
    11: 2,  # Image ranking
    12: 3,  # Narration generation
    13: 3,  # Timeline synchronization
    14: 4,  # Video assembly
}


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Oswald:wght@300;400;500&family=Source+Sans+3:wght@300;400;500;600&display=swap');

:root {
  --bg-deep: #09090d;
  --bg-surface: #121219;
  --bg-raised: #191923;
  --ink: #f4f2ed;
  --muted: #a09a92;
  --accent: #e11d48;
  --accent-soft: rgba(225, 29, 72, 0.22);
  --gold: #d4a853;
  --line: #2b2b35;
}

.stApp {
  background:
    radial-gradient(circle at 10% 5%, rgba(212, 168, 83, 0.09), transparent 40%),
    radial-gradient(circle at 90% 15%, rgba(225, 29, 72, 0.08), transparent 35%),
    linear-gradient(180deg, #0b0b10 0%, #09090d 100%) !important;
}

div[data-testid="stAppViewContainer"] > .main .block-container {
  max-width: 1120px;
  padding-top: 1rem;
  padding-bottom: 3rem;
}

* {
  font-family: "Source Sans 3", sans-serif !important;
}

h1, h2, h3, [data-testid="stMarkdownContainer"] p strong {
  color: var(--ink);
}

.logo-container {
  text-align: center;
  margin: 0.4rem 0 1.8rem;
}

.logo-icon {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
}

.logo-icon svg {
  width: 44px;
  height: 44px;
  color: var(--gold);
}

.logo-text {
  font-family: "Bebas Neue", sans-serif !important;
  font-size: clamp(2.1rem, 4vw, 4.2rem);
  letter-spacing: 0.16em;
  color: transparent !important;
  background: linear-gradient(130deg, #f4f2ed 0%, #d4a853 40%, #e11d48 100%);
  -webkit-background-clip: text;
  background-clip: text;
}

.logo-tagline {
  margin-top: 0.2rem !important;
  font-family: "Oswald", sans-serif !important;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 0.9rem;
  color: var(--muted) !important;
}

.pipeline-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.45rem;
  margin: 1.1rem 0 1.8rem;
}

.pipeline-stage {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0.5rem 0.95rem;
  background: linear-gradient(180deg, var(--bg-raised), var(--bg-surface));
}

.pipeline-stage.active {
  border-color: var(--accent);
  box-shadow: 0 0 26px var(--accent-soft);
}

.pipeline-icon {
  width: 16px;
  height: 16px;
  color: var(--gold);
}

.pipeline-label {
  font-family: "Oswald", sans-serif !important;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink);
  font-size: 0.76rem;
}

.pipeline-arrow {
  color: #51515d;
  padding: 0 0.18rem;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(18, 18, 25, 0.9), rgba(12, 12, 18, 0.95));
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
  background: #0f0f15 !important;
  border: 1px solid var(--line) !important;
  color: var(--ink) !important;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 1px var(--gold) !important;
}

div[data-baseweb="radio"] label {
  border-radius: 8px !important;
}

[data-testid="stButton"] button[kind="primary"] {
  font-family: "Bebas Neue", sans-serif !important;
  letter-spacing: 0.14em;
  font-size: 1.2rem;
  border: none !important;
  background: linear-gradient(140deg, #e11d48 0%, #c1123e 55%, #8a0e2c 100%) !important;
  box-shadow: 0 10px 30px rgba(225, 29, 72, 0.28);
}

[data-testid="stButton"] button[kind="primary"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 34px rgba(225, 29, 72, 0.36);
}

.terminal-container {
  margin-top: 1rem;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #0a0a0d;
  overflow: hidden;
}

.terminal-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #14141c;
  border-bottom: 1px solid var(--line);
  padding: 0.6rem 0.9rem;
}

.terminal-dot { width: 10px; height: 10px; border-radius: 999px; }
.terminal-dot.red { background: #ef4444; }
.terminal-dot.yellow { background: #eab308; }
.terminal-dot.green { background: #22c55e; }

.terminal-title {
  margin-left: auto;
  color: var(--muted);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  font-family: "Oswald", sans-serif !important;
}

.terminal-content {
  padding: 0.95rem;
  max-height: 360px;
  overflow-y: auto;
  font-family: "JetBrains Mono", monospace !important;
}

.terminal-content code {
  color: #efe7d3 !important;
  white-space: pre-wrap;
  font-size: 0.83rem;
  line-height: 1.45;
}

.video-container {
  margin-top: 1.2rem;
  border: 2px solid rgba(212, 168, 83, 0.65);
  border-radius: 12px;
  background: linear-gradient(180deg, #171721, #101017);
}

.video-frame {
  padding: 0.65rem;
  border-bottom: 1px solid var(--line);
}

.video-title {
  margin: 0 !important;
  color: var(--gold) !important;
  font-family: "Bebas Neue", sans-serif !important;
  letter-spacing: 0.18em;
  text-align: center;
}

#MainMenu, footer {
  visibility: hidden !important;
}

header[data-testid="stHeader"] {
  background: transparent !important;
}

@media (max-width: 768px) {
  .pipeline-container {
    justify-content: flex-start;
  }
}
</style>
"""


def _build_command(topic, max_websites, tts_provider):
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
    for line in reversed(logs):
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def render_custom_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header():
    st.markdown(
        """
    <div class="logo-container">
        <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"/>
                <polygon points="10,8 16,12 10,16" fill="currentColor" stroke="none"/>
            </svg>
            <span class="logo-text">NARRATE-AI</span>
        </div>
        <p class="logo-tagline">Transform any topic into cinematic documentary</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_pipeline(active_stage=0):
    stage_html = '<div class="pipeline-container">'
    for i, (icon, label) in enumerate(PIPELINE_STAGES):
        active = i == active_stage
        active_class = "active" if active else ""
        icon_svg = get_icon(icon)
        stage_html += f"""
        <div class="pipeline-stage {active_class}">
            <svg class="pipeline-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                {icon_svg}
            </svg>
            <span class="pipeline-label">{label}</span>
        </div>
        """
        if i < len(PIPELINE_STAGES) - 1:
            stage_html += '<span class="pipeline-arrow">→</span>'

    stage_html += "</div>"
    st.markdown(stage_html, unsafe_allow_html=True)


def _infer_stage_from_log_line(line, current_stage):
    """Infer pipeline stage index from one log line."""
    match = re.search(r"\[PIPELINE\]\s+Step\s+(\d+):", line)
    if match:
        step_number = int(match.group(1))
        return STEP_STAGE_BY_NUMBER.get(step_number, current_stage)

    if line.startswith("[VIDEO]") or "Completed successfully:" in line:
        return 4

    return current_stage


def get_icon(name):
    icons = {
        "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
        "file-text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
        "image": '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
        "volume-2": '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>',
        "film": '<rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/>',
        "folder": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
        "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
        "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v6c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 11v6c0 1.7 4 3 9 3s9-1.3 9-3v-6"/>',
    }
    return icons.get(name, "")


def render_terminal(logs):
    if not logs:
        return

    escaped_logs = escape("\n".join(logs))
    st.markdown(
        f"""
    <div class="terminal-container">
        <div class="terminal-header">
            <span class="terminal-dot red"></span>
            <span class="terminal-dot yellow"></span>
            <span class="terminal-dot green"></span>
            <span class="terminal-title">PRODUCTION LOG</span>
        </div>
        <div class="terminal-content">
            <code>{escaped_logs}</code>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_video_player(video_path):
    if not video_path or not Path(video_path).exists():
        return

    st.markdown(
        f"""
    <div class="video-container">
        <div class="video-frame">
            <p class="video-title">FINAL OUTPUT</p>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.video(str(video_path))


def main():
    st.set_page_config(
        page_title="Narrate-AI | Documentary Generator",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Render CSS first
    render_custom_css()

    render_header()
    pipeline_box = st.empty()
    current_stage = 0
    with pipeline_box.container():
        render_pipeline(current_stage)

    with st.container(border=True):
        st.markdown("### Documentary Setup")
        topic = st.text_input(
            "Topic",
            value="Apollo Program",
            help="Enter any historical topic, event, person, or concept",
            key="topic_input",
        )

        col1, _ = st.columns(2)
        with col1:
            max_websites = st.number_input(
                "Max Websites",
                min_value=1,
                step=1,
                value=DEFAULT_MAX_WEBSITES,
                help="Number of websites to research, the model also will use its own knowledge base to generate the script, so you can keep it low.",
            )

        has_elevenlabs_key = bool(os.getenv("ELEVENLABS_API_KEY"))

        tts_provider = st.radio(
            "TTS Provider",
            options=["elevenlabs", "edge_tts"],
            index=0 if DEFAULT_TTS_PROVIDER == "elevenlabs" else 1,
            horizontal=True,
        )

        if tts_provider == "elevenlabs" and not has_elevenlabs_key:
            st.warning(
                "⚠️ ElevenLabs API key not found. Set ELEVENLABS_API_KEY or use Edge TTS."
            )

        if tts_provider == "edge_tts":
            st.info("ℹ️ Edge TTS: Free Microsoft voices, no API key required.")

    run_clicked = st.button(
        "▶ GENERATE DOCUMENTARY", type="primary", use_container_width=True
    )

    if not run_clicked:
        return

    topic = topic.strip()
    if not topic:
        st.error("Topic is required.")
        return

    command = _build_command(
        topic=topic,
        max_websites=int(max_websites),
        tts_provider=tts_provider,
    )

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
        next_stage = _infer_stage_from_log_line(line, current_stage)
        if next_stage != current_stage:
            current_stage = next_stage
            with pipeline_box.container():
                render_pipeline(current_stage)
        with log_box.container():
            render_terminal(logs)

    return_code = process.wait()

    if return_code != 0:
        st.error(f"Pipeline failed with exit code {return_code}.")
        return

    st.success("✓ Documentary generated successfully!")
    with pipeline_box.container():
        render_pipeline(4)

    final_video = _extract_value(logs, "Final video:")
    if final_video and Path(final_video).exists():
        render_video_player(final_video)


if __name__ == "__main__":
    main()
