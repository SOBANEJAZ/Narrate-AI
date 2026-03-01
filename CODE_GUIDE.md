# Narrate-AI Code Guide

This guide explains how the Narrate-AI codebase works, its architecture, and how to understand the code.

## Overview

Narrate-AI is a documentary video generator that takes a topic and produces a narrated slideshow video. It uses AI agents for research, script writing, and image selection, combined with various services for web search, vector storage, text-to-speech, and video assembly.

## Architecture

The project follows a pipeline architecture with specialized agents and services:

```
Entry Points
    │
    ├── main.py (CLI)
    └── streamlit_app.py (Web UI)
            │
            ▼
    ┌─────────────────────────────────────────────────────┐
    │                   core/pipeline.py                   │
    │         Orchestrates the documentary pipeline        │
    └─────────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────────┐
    │                      Agents                          │
    │  (AI-powered decision making using Groq LLM)        │
    ├─────────────────────────────────────────────────────┤
    │  narrative_architect.py  → Creates documentary plan │
    │  query_generator.py     → Generates search queries │
    │  script_writer.py       → Writes narration script  │
    │  image_segmentation.py  → Determines image zones    │
    └─────────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────────┐
    │                     Services                        │
    │            (Domain-specific utilities)             │
    ├─────────────────────────────────────────────────────┤
    │  research/  → Web crawling & source discovery       │
    │  rag/      → Vector database & semantic search     │
    │  images/   → Image retrieval & CLIP ranking       │
    │  audio/    → Text-to-speech synthesis             │
    │  video/    → Video assembly & rendering           │
    └─────────────────────────────────────────────────────┘
```

## Pipeline Flow

The documentary generation happens in 4 phases:

### Phase 1: Research & Context Building

1. **Narrative Architect** (`agents/narrative_architect.py`)
   - Analyzes the topic using Groq LLM
   - Creates a structured documentary outline with sections
   - Determines tone, pacing, and target duration

2. **Source Discovery** (`services/research/crawler.py`)
   - Uses Serper.dev (Google Search) to find web sources
   - Prioritizes authoritative sources (.edu, .gov, Wikipedia, etc.)
   - Returns ranked list of URLs

3. **Content Crawling** (`services/research/crawler.py`)
   - Crawls each discovered website using crawl4ai
   - Extracts main content and chunks it into 500-word segments
   - Creates research notes with source attribution

4. **RAG Indexing** (`services/rag/manager.py`)
   - Converts text chunks into vector embeddings (MiniLM-L12-v2)
   - Stores embeddings in Pinecone vector database
   - Enables semantic similarity search

5. **Query Generation** (`agents/query_generator.py`)
   - For each section of the outline, generates semantic search queries
   - These queries retrieve relevant context from the vector DB

6. **Semantic Retrieval** (`services/rag/manager.py`)
   - Searches Pinecone using generated queries
   - Retrieves most relevant text chunks for each section

### Phase 2: Content Generation

7. **Script Writer** (`agents/script_writer.py`)
   - Uses retrieved research notes + LLM knowledge
   - Generates spoken narration script in documentary style
   - Written for audio narration (spoken language, not formal)

8. **Image Segmentation** (`agents/image_segmentation.py`)
   - Analyzes script to find natural breakpoints for image changes
   - Considers topic shifts, location changes, time periods
   - Creates image zones (start/end sentence numbers)

9. **Visual Intelligence** (integrated into image services)
   - For each segment, generates optimized search queries
   - Creates CLIP-ready descriptions of ideal images

### Phase 3: Image Retrieval

10. **Image Retrieval** (`services/images/retrieval.py`)
    - Searches Google Images via Serper.dev
    - Downloads candidate images in parallel
    - Uses caching to avoid redundant downloads

11. **Image Ranking** (`services/images/ranking.py`)
    - Evaluates candidates using OpenCLIP vision-language model
    - Compares images against segment descriptions
    - Combines CLIP similarity with image quality metrics
    - Selects best image for each segment

### Phase 4: Production

12. **Narration** (`services/audio/narration.py`)
    - Synthesizes audio from script segments
    - Supports ElevenLabs (premium) or Edge TTS (free)
    - Generates WAV audio files

13. **Timeline Building** (`services/video/video.py`)
    - Combines image, audio, and timing info
    - Calculates durations from audio file lengths
    - Creates synchronized timeline entries

14. **Video Assembly** (`services/video/video.py`)
    - Renders final MP4 video
    - Applies zoom effects to images
    - Composites with background (black or blur)
    - Concatenates all segments

## Understanding Key Files

### core/config.py

Manages configuration from environment variables and defaults. Provides:
- `create_default_config()` - Returns dict with all defaults
- `create_config_from_env()` - Overrides with env vars
- `update_config()` - Immutable config updates
- `get_groq_client()` - Singleton Groq API client

### core/pipeline.py

The main orchestration file. `run_pipeline()` executes all steps in sequence:
1. Create run directory
2. Build narrative plan
3. Discover and crawl sources
4. Index to Pinecone
5. Generate queries and retrieve notes
6. Write script
7. Segment for images
8. Retrieve and rank images
9. Synthesize audio
10. Build timeline
11. Assemble video
12. Save manifest

### core/models.py

Defines data structures:
- Pydantic models for LLM response validation (NarrativePlan, ImageSegmentation, etc.)
- Factory functions for creating plain dicts (create_script_segment, create_timeline_item)

### core/cache.py

Multi-layer caching system:
- Memory cache (fast, ephemeral)
- Disk cache (persistent, keyed by namespace:key hash)
- Used for web search results, crawled pages, etc.

### core/llm.py

Utilities for working with LLM responses:
- `extract_json()` - Parses JSON from LLM text output
- `validate_pydantic()` - Validates against Pydantic model

### agents/*.py

Each agent uses Groq LLM with specific prompts:

- **narrative_architect**: Creates documentary structure (sections, objectives, durations)
- **query_generator**: Generates semantic search queries for RAG
- **script_writer**: Writes narration script from plan + context
- **image_segmentation**: Determines where images should change in script

### services/research/crawler.py

Web research pipeline:
- `discover_sources()` - Search for authoritative URLs
- `crawl_and_build_notes()` - Extract content and chunk it
- `_is_authoritative()` - Checks domain hints (.edu, .gov, etc.)
- `_source_score()` - Ranks sources by authority

### services/rag/manager.py

Vector database operations using Pinecone:
- `PineconeManager` class - Handles index creation, upserts, queries
- `embed_text()` - Uses MiniLM-L12-v2 for embeddings
- Falls back to direct note use if Pinecone unavailable

### services/images/retrieval.py

Image search and download:
- `retrieve_images()` - Main function for segment images
- `_search_images()` - Serper.dev image search API
- `_download_image_worker()` - Parallel image downloader
- Uses caching to avoid re-downloading

### services/images/ranking.py

CLIP-based image selection:
- `create_ranking_state()` - Initializes OpenCLIP model
- `rank_images()` - Main ranking function
- `_rank_with_clip()` - CLIP embedding + similarity
- `_calculate_quality_score()` - Resolution + sharpness metrics

### services/audio/*.py

Text-to-speech with multiple providers:
- **elevenlabs.py** - Premium TTS (API key required)
- **edge_tts_client.py** - Free Microsoft TTS
- **factory.py** - Creates appropriate synthesizer
- **narration.py** - Orchestrates audio generation

### services/video/video.py

Video assembly:
- `build_timeline()` - Creates timeline from segments
- `assemble_video()` - Renders final MP4
- `zoom_in_effect()` - Smooth zoom animation using PIL
- `_build_segment_clip()` - Creates single segment video

## Data Flow

```
Topic String
    │
    ▼
NarrativePlan (sections, objectives, tone, pacing)
    │
    ▼
[Research] → Sources List → Research Notes → Pinecone Vectors
    │
    ▼
[Queries] → Semantic Search → Retrieved Notes
    │
    ▼
Script (narrative text)
    │
    ▼
ImageSegmentation (zones with sentence ranges)
    │
    ▼
ScriptSegments (text + zone info)
    │
    ├──→ [Image Retrieval] → Candidate Images
    │                              │
    │                              ▼
    │                         Ranked Images
    │                              │
    │                              ▼
    │                         Selected Image
    │
    └──→ [TTS] → Audio Files
                    │
                    ▼
            Timeline Items
            (image + audio + duration)
                    │
                    ▼
            Final Video MP4
```

## Key Design Patterns

### 1. Agent Pattern

Each agent follows a similar structure:
1. Takes context (LLM client + config) + input data
2. Constructs prompt with instructions
3. Calls Groq API
4. Parses JSON response
5. Returns structured data (Pydantic models)

### 2. Service Layer

Services are domain-specific utilities that agents use:
- Stateless functions where possible
- Configuration passed as dict
- Clear input/output contracts
- Caching at appropriate levels

### 3. Multi-Layer Cache

`MultiLayerCache` provides:
- Fast memory lookup for recent operations
- Persistent disk cache for expensive operations
- Namespace isolation (research, crawl, images, etc.)
- SHA256 key hashing

### 4. Factory Pattern

Used in audio service:
- `create_tts_synthesizer()` - Returns appropriate function
- Provider-agnostic interface
- Easy to add new TTS providers

### 5. Pipeline Pattern

`core/pipeline.py` orchestrates:
- Sequential execution of phases
- Clear logging at each step
- Error handling with descriptive messages
- Output files at each stage for debugging

## Common Operations

### Adding a New Agent

1. Create `agents/your_agent.py`
2. Import and use `extract_json()` from `core.llm`
3. Define Pydantic model in `core/models.py` if needed
4. Export from `agents/__init__.py`
5. Add to pipeline in `core/pipeline.py`

### Adding a New TTS Provider

1. Create `services/audio/your_provider.py`
2. Implement `synthesize_your_tts(text, out_path, config)` function
3. Add to factory in `services/audio/factory.py`
4. Update `create_tts_synthesizer()` match case

### Debugging Pipeline Issues

Check intermediate outputs in `runs/<timestamp>-<topic>/`:
- `script.txt` - Generated script
- `narrative_plan.json` - Documentary structure
- `sources.json` - Research sources
- `notes.json` - Raw research notes
- `retrieved_notes.json` - RAG-retrieved context
- `timeline.json` - Final timeline
- `manifest.json` - Complete metadata

## Configuration

Configuration is managed through:
1. Default values in `core/config.py`
2. Environment variables (loaded from `.env`)
3. CLI arguments (for main.py) or UI inputs (for streamlit_app)

Key settings:
- `run_root` - Output directory
- `max_websites` - Sources to crawl
- `max_queries_per_segment` - Image searches per segment
- `sentence_span_per_segment` - Sentences per video clip
- `tts_provider` - "elevenlabs" or "edge_tts"
- `background_mode` - "black" or "blur"

## Testing Approach

The project uses pytest. Run tests with:
```bash
pytest
```

Key test areas:
- LLM response parsing
- Pipeline step integration
- Image ranking logic
- Video assembly

## Performance Considerations

- **Caching**: Web searches and crawled pages are cached
- **Parallel Downloads**: Image retrieval uses ThreadPoolExecutor
- **GPU Acceleration**: CLIP ranking uses CUDA if available
- **Model Choices**: Groq for fast LLM, MiniLM for quick embeddings
