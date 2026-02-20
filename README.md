# Narrate-AI

Narrate-AI turns a single topic into a narrated documentary video. It researches the topic, writes a script, finds matching images, generates narration, and assembles everything into a video.

## Table of Contents

- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [CLI Usage](#cli-usage)
- [Output Files](#output-files)
- [Architecture](#architecture)
- [Services](#services)
- [Extending the System](#extending-the-system)

## How It Works

The pipeline runs thirteen steps:

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

## Project Structure

```
Narrate-AI/
├── agents/                    # Agent functions that perform core tasks
│   ├── __init__.py
│   ├── narrative_architect.py # Structures documentary outline
│   ├── query_generator.py     # Generates semantic search queries
│   ├── script_writer.py       # Writes narration script
│   └── visual_intelligence.py # Generates image descriptions
├── services/                  # Domain-specific service modules
│   ├── audio/                 # Audio synthesis (TTS)
│   │   ├── base.py
│   │   ├── elevenlabs.py
│   │   ├── edge_tts_client.py
│   │   ├── factory.py
│   │   └── narration.py
│   ├── images/                # Image retrieval and ranking
│   │   ├── retrieval.py
│   │   ├── ranking.py
│   │   └── placement.py
│   ├── video/                 # Video assembly
│   │   └── video.py
│   ├── rag/                   # Vector database management
│   │   └── manager.py
│   ├── research/              # Web research and crawling
│   │   └── crawler.py
│   └── __init__.py
├── core/                      # Core utilities and models
│   ├── __init__.py
│   ├── cache.py               # Multi-layer caching system
│   ├── config.py              # Configuration and Groq client management
│   ├── llm.py                 # LLM utility functions
│   ├── models.py              # Pydantic data models
│   ├── pipeline.py            # Main documentary generation pipeline
│   └── text_utils.py          # Text processing utilities
├── main.py                    # CLI entry point
├── streamlit_app.py           # Web UI
└── README.md                  # This file
```

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

## Configuration

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

## CLI Usage

### Streamlit UI

Launch the web interface:

```bash
streamlit run streamlit_app.py
```

The UI lets you:
- Enter a documentary topic
- Configure all pipeline options
- Select TTS provider (ElevenLabs or Edge TTS)
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

### Design Principles

Narrate-AI uses:

- **Pydantic models** for structured data validation
- **Service modules** organized by domain (audio, video, images, RAG, research)
- **Agent functions** that operate on config and Groq client context
- **Multi-layer caching** to avoid redundant API calls
- **Composition over inheritance** for flexibility

### Pipeline Flow

```python
from core.config import create_config_from_env, get_groq_client
from core.pipeline import run_pipeline

config = create_config_from_env()
result = run_pipeline(config, "Your Topic")
print(f"Video saved to: {result.final_video_path}")
```

The pipeline passes an `agent_context` dict to all agents:

```python
agent_context = {
    "groq_client": groq_client,
    "config": config,
}
```

Agents call Groq directly and use utility functions for JSON parsing:

```python
from core.llm import extract_json, validate_pydantic

response = groq_client.chat.completions.create(
    messages=[{"role": "user", "content": prompt}],
    model=config["groq_model"],
    temperature=0.2,
)

json_data = extract_json(response.choices[0].message.content)
result = validate_pydantic(json_data, MyPydanticModel)
```

## Services

### Audio Service (`services/audio/`)

Synthesizes narration audio using pluggable TTS providers:

- **ElevenLabs**: High-quality multilingual voices
- **Edge TTS**: Free Microsoft-powered alternative

### Video Service (`services/video/`)

Assembles the final MP4 with:

- Centered image display with subtle zoom effects
- Synchronized audio and image transitions
- Configurable resolution and frame rate

### Images Service (`services/images/`)

Retrieves and ranks images for each script segment:

- **Retrieval**: Downloads candidates from DuckDuckGo image search
- **Ranking**: Uses OpenCLIP semantic matching (with keyword fallback)
- **Placement**: Segments script for optimal visual pacing

### RAG Service (`services/rag/`)

Manages vector database operations with Pinecone:

- Embeds research notes with Gemini
- Stores notes with metadata (topic, source, text)
- Retrieves notes via semantic similarity search

### Research Service (`services/research/`)

Crawls the web and builds research context:

- Discovers authoritative sources with DuckDuckGo
- Crawls pages and chunks content (500 words, 100 word overlap)
- Extracts text without boilerplate

## Extending the System

### Adding a New Agent

Create a new file in `agents/`:

```python
"""My custom agent."""

from groq import Groq
from core.llm import extract_json, validate_pydantic
from core.models import MyModel

def my_agent(context, data):
    """Agent function signature.
    
    Args:
        context: Dict with 'groq_client' and 'config' keys
        data: Input data
        
    Returns:
        Pydantic-validated result
    """
    groq_client = context["groq_client"]
    config = context["config"]
    
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": "Your prompt"}],
        model=config["groq_model"],
        temperature=0.2,
    )
    
    json_data = extract_json(response.choices[0].message.content)
    return validate_pydantic(json_data, MyModel)
```

Export it in `agents/__init__.py`:

```python
from agents.my_agent import my_agent

__all__ = ["my_agent"]
```

Use it in the pipeline:

```python
from agents import my_agent

result = my_agent(agent_context, input_data)
```

### Adding a New Service

Create a new module in `services/`:

```
services/my_service/
├── __init__.py
└── handler.py
```

Implement your service following the same pattern as existing services, then use it in the pipeline or agents as needed.

## RAG Pipeline

Narrate-AI uses Retrieval-Augmented Generation to produce more accurate scripts:

1. Research notes are embedded with Gemini and stored in Pinecone
2. Each script section generates semantic search queries
3. Similarity search retrieves the most relevant context
4. The LLM uses this context to generate accurate narration
