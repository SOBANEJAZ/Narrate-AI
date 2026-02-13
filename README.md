# Narrate-AI

Narrate-AI is a multi-agent documentary generator that turns a single topic into a narrated slideshow video.

The pipeline implements the plan in `prompt.md`:

1. Narrative Architect: builds documentary structure.
2. Website Discovery: finds authoritative sources with DDGS.
3. Crawl + RAG Notes: crawls pages and chunks notes.
4. Script Writer: generates spoken narration script.
5. Image Placement: splits script into visual segments.
6. Visual Intelligence: generates search queries + CLIP-ready description per segment.
7. Image Retrieval: downloads candidates from DDGS image search.
8. Image Ranking: ranks images with OpenCLIP (fallback ranking if CLIP is unavailable).
9. Narration: synthesizes per-segment audio through ElevenLabs (fallback local audio if not configured).
10. Timeline + Assembly: produces final `1280x720` MP4 with centered images and aspect-ratio-safe background fill.

## Quick Start

### 1) Install dependencies

```bash
uv sync
```

Optional extras:

```bash
uv sync --extra clip --extra crawl --extra crewai
```

### 2) Configure environment (optional but recommended)

Set any available providers:

```bash
export GROQ_API_KEY="..."
export CEREBRAS_API_KEY="..."
export ELEVENLABS_API_KEY="..."
export ELEVENLABS_VOICE_ID="JBFqnCBsd6RMkjVDRZzb"
export ELEVENLABS_MODEL_ID="eleven_multilingual_v2"
```

If these are missing, the pipeline still runs with deterministic fallbacks.

### 3) Run full documentary generation

```bash
python main.py "History of the Wright Brothers"
```

Useful options:

```bash
python main.py "Apollo Program" \
  --background blur \
  --max-websites 4 \
  --max-queries 5 \
  --images-per-query 5 \
  --sentence-span 3
```

Default values for all `--` options:

- `--run-root`: `runs`
- `--background`: `black`
- `--max-websites`: `4`
- `--max-queries`: `5`
- `--images-per-query`: `5`
- `--sentence-span`: `3`

## Streamlit UI

Launch the UI:

```bash
streamlit run streamlit_app.py
```

The UI runs the same pipeline command as `main.py`, shows live logs during execution, and displays the generated video when complete.

Artifacts are written to `runs/<timestamp>-<topic>/`:

- `script.txt`
- `narrative_plan.json`
- `sources.json`
- `notes.json`
- `timeline.json`
- `manifest.json`
- `final_output.mp4`

## Starter Timeline Module

The folder `moviepy_starter/` contains a standalone timeline/assembly script for pre-existing image/audio pairs:

```bash
python moviepy_starter/main.py moviepy_starter/files
```

It outputs `moviepy_starter/files/final_output.mp4` at `1280x720`.
