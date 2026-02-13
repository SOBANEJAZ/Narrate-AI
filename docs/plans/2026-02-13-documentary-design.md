# Narrate-AI Documentary Pipeline Design

## Goal

Implement the full automated documentary generation flow described in `prompt.md`:

- Topic input
- Multi-agent research and writing
- Segment-level visual planning
- Image retrieval and ranking
- Narration synthesis
- Timeline synchronization
- Final `1280x720` slideshow-style MP4 output

## Architecture

The implementation is organized as a pipeline of focused agents in `narrate_ai/agents/`:

1. `NarrativeArchitectAgent`
   - Creates documentary structure (tone, pacing, sections, durations).
   - Uses Groq for compact decision outputs when configured.

2. `ResearchPipeline`
   - Discovers sources with DDGS.
   - Crawls source pages with `crawl4ai` when available, otherwise HTTP + BeautifulSoup fallback.
   - Chunks content into reusable notes.

3. `ScriptWriterAgent`
   - Generates spoken narration script from plan + notes.
   - Uses Cerebras for larger context writing when configured.

4. `ImagePlacementAgent`
   - Splits script into sentence-range segments for visual changes.

5. `VisualIntelligenceAgent`
   - Produces dual output per segment in a single reasoning step:
     - Search queries for retrieval
     - Natural language visual description for CLIP ranking

6. `ImageRetrievalAgent`
   - Retrieves candidates from DDGS image search.
   - Downloads and deduplicates images.

7. `ImageRankingAgent`
   - Ranks candidates via OpenCLIP ViT-B/16 when installed.
   - Falls back to keyword-overlap scoring if CLIP is unavailable.

8. `NarrationAgent`
   - Calls ElevenLabs TTS when configured.
   - Generates deterministic fallback audio for offline execution.

9. `Timeline + Assembly`
   - `build_timeline` aligns segment durations to narration.
   - `assemble_video` renders final MP4:
     - `1280x720`
     - centered images
     - aspect-ratio safe fit
     - black or blurred background fill
     - smooth sequential transitions

## Caching Strategy

`MultiLayerCache` provides:

- In-memory cache for current run
- Disk cache per run (`runs/.../cache`) for reproducibility and deduplication

Used for source discovery, crawl content, and image search responses.

## Execution Entrypoints

- Full pipeline: `main.py`
- Starter timeline-only module: `moviepy_starter/main.py`

## Validation Performed

- Python compile checks for all modules.
- Full pipeline run in `.venv`:
  - `python main.py "Test Topic" ...`
  - Generated run artifacts and final MP4.
- Starter module run in `.venv`:
  - `python moviepy_starter/main.py moviepy_starter/files`
  - Generated final MP4 from existing segment assets.
