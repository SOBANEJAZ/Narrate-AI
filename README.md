# Narrate-AI

Narrate-AI turns a single topic into a narrated documentary video. It researches the topic, writes a script, finds matching images, generates narration, and assembles everything into a video.

## How It Works

The pipeline runs eleven steps:

1. **Narrative Architect**: Builds documentary structure
2. **Website Discovery**: Finds authoritative sources with DDGS
3. **Crawl + RAG Notes**: Crawls pages and chunks notes (500 words, 100 word overlap)
4. **Index to Pinecone**: Embeds notes with Gemini for semantic search
5. **Generate RAG Queries**: Creates semantic search queries for each section
6. **Semantic Retrieval**: Retrieves relevant notes from vector DB using similarity search
7. **Script Writer**: Generates spoken narration script using retrieved context
8. **Image Placement**: Splits script into visual segments
9. **Visual Intelligence**: Generates search queries and CLIP-ready descriptions
10. **Image Retrieval**: Downloads candidates from DDGS image search
11. **Image Ranking**: Ranks images with OpenCLIP (falls back to keyword matching)
12. **Narration**: Synthesizes audio with ElevenLabs or Edge TTS
13. **Timeline + Assembly**: Produces `1280x720` MP4 with centered images at 15fps

## Quick Start

### Install Dependencies

```bash
uv sync
```

Optional extras:

```bash
uv sync --extra clip --extra crawl --extra crewai
```

### Configure Environment

Set any available providers:

```bash
# LLM Providers (at least one required)
export GROQ_API_KEY="..."
export CEREBRAS_API_KEY="..."

# Text-to-Speech
export ELEVENLABS_API_KEY="..."
export ELEVENLABS_VOICE_ID="JBFqnCBsd6RMkjVDRZzb"
export ELEVENLABS_MODEL_ID="eleven_multilingual_v2"
export EDGE_TTS_VOICE="en-US-AriaNeural"

# Vector Search (RAG)
export PINECONE_API="..."
export PINECONE_ENV="us-east-1"
export GEMINI_API_KEY="..."
```

The pipeline runs without API keys using fallback options.

### Generate a Documentary

```bash
python main.py "History of the Wright Brothers"
```

With options:

```bash
python main.py "Apollo Program" \
  --background blur \
  --max-websites 4 \
  --max-queries 5 \
  --images-per-query 5 \
  --sentence-span 3 \
  --tts-provider edge_tts
```

**CLI Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--run-root` | `runs` | Directory for output files |
| `--background` | `black` | Background mode (`black` or `blur`) |
| `--max-websites` | `4` | Sources to research |
| `--max-queries` | `5` | Image searches per segment |
| `--images-per-query` | `5` | Images to download per search |
| `--sentence-span` | `3` | Sentences per video segment |
| `--tts-provider` | `elevenlabs` | Voice provider (`elevenlabs` or `edge_tts`) |

### Text-to-Speech Options

**ElevenLabs** (default): High-quality voices. Requires `ELEVENLABS_API_KEY`.

**Edge TTS**: Free alternative using Microsoft's Edge TTS. No API key required.

Set the provider via CLI (`--tts-provider`) or environment variable (`TTS_PROVIDER`).

## Streamlit UI

Launch the web interface:

```bash
streamlit run streamlit_app.py
```

The UI lets you:
- Enter a documentary topic
- Configure all pipeline options
- **Select TTS provider** (ElevenLabs or Edge TTS)
- Watch live logs during generation
- View the completed video

## Output Files

Artifacts write to `runs/<timestamp>-<topic>/`:

- `script.txt` — Generated narration script
- `narrative_plan.json` — Documentary structure
- `sources.json` — Research sources
- `notes.json` — Extracted research notes
- `retrieved_notes.json` — Notes retrieved via semantic search
- `timeline.json` — Video timeline
- `manifest.json` — Complete run metadata
- `final_output.mp4` — Completed documentary

## Architecture

The codebase uses Pydantic models for structured data. Agents are functions that accept configuration and return Pydantic-validated results. This approach ensures type safety and makes the code easier to test and reason about.

```python
from core.config import create_config_from_env
from pipeline import run_pipeline

config = create_config_from_env()
result = run_pipeline(config, "Your Topic")
print(f"Video saved to: {result.final_video_path}")
```

### RAG Pipeline

Narrate-AI uses Retrieval-Augmented Generation to produce more accurate scripts:

1. Research notes are embedded with Gemini and stored in Pinecone
2. Each script section generates semantic search queries
3. Similarity search retrieves the most relevant context
4. The LLM uses this context to generate accurate narration
