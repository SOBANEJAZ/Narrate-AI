---

# 🎬 Automated History Documentary Generation System

## Multi-Agent CrewAI Architecture (NotebookLM-Style Slideshow)

---

## 🎯 Objective

Build an automated documentary generator that:

* Accepts any topic as input
* Researches factual information using RAG
* Generates a narrated script
* Determines where images should appear
* Retrieves and ranks relevant images
* Generates narration using latest Qwen TTS
* Synchronizes visuals with audio
* Produces a final **1280x720 slideshow-style video**
* Centers all images regardless of resolution

The final output should resemble NotebookLM-style video generation:

* Images in foreground (slideshow)
* Narration in background
* Smooth timing and transitions

---

# 🧠 Full Multi-Agent Architecture

---

## 1 Narrative Architect Agent

**Purpose:** Control documentary structure and storytelling.

Responsibilities:

* Break topic into:

  * Introduction
  * Core Sections
  * Transitions
  * Conclusion
* Define tone and pacing
* Decide approximate length per section
* Ensure logical narrative flow

---

## 2 Research Pipeline

### Step A — Website Discovery

Use:

```python
from ddgs import DDGS
```

Purpose:

* Discover high-quality URLs related to topic
* Return Top N authoritative websites
* Start with top 4 websites
---

### Step B — Crawl + RAG

* Pass discovered URLs to `crawl4ai`
* Scrape structured content
* Chunk and embed data
* Store in agentic cache
* Provide structured notes to Script Agent

---

## 3 Script Writing Agent

**Input:** Structured research notes
**Output:** Documentary narration script

Requirements:

* Optimized for spoken narration
* Clear storytelling
* Avoid overly academic tone
* Maintain engagement

---

## 4 Image Placement Agent

**Purpose:** Decide visual segmentation.

Responsibilities:

* Analyze final script
* Define sentence ranges for image changes

Example:

* Sentence 1–3 → Image A
* Sentence 4–6 → Image B

Output:

```json
[
  {
    "segment_id": 1,
    "text_range": "Sentence 1–3"
  }
]
```

---

# 5 Visual Intelligence Pipeline (Enhanced)

This section includes the improved dual-output architecture.

---

## Step 1 — Script Segment

Raw narration text for a specific segment.

Example:

> The Wright brothers achieved the first powered flight in 1903.

---

## Step 2 — LLM Generates TWO Outputs (Single Call)

From the same reasoning step, generate:

### A) Search Queries (Keyword-Optimized)

Used for DDGS image search.

Example:

* "Wright brothers first flight 1903"
* "Kitty Hawk airplane 1903"
* "early aviation black and white photo"

Optimized for:

* Search engines
* Entity matching
* Historical specificity

---

### B) Visual Description (Natural Language Sentence)

Used for OpenCLIP embedding comparison.

Example:

> "A historic black and white photograph of the Wright brothers' first powered airplane flight at Kitty Hawk in 1903."

Optimized for:

* Cross-modal semantic alignment
* Visual clarity
* Contextual accuracy

---

## Why This Dual Output?

Search queries ≠ CLIP prompts.

| Text Type          | Optimized For                  |
| ------------------ | ------------------------------ |
| Search Queries     | Web retrieval                  |
| Visual Description | Image–text semantic comparison |

CLIP performs better with natural descriptive sentences, not fragmented keyword strings.

---

# 6 Image Retrieval Agent

Using:

```python
from ddgs import DDGS
```

Process:

* Execute multiple search queries at once
* Retrieve 5 images per query
* Total: 5 queries × 5 images = 25 images
* Use agentic cache to prevent duplicate requests



# 7 Image Ranking Agent (OpenCLIP)

Model:

* OpenCLIP ViT-B/16

Process:

1. Embed Visual Description text
2. Embed all candidate images
3. Compute cosine similarity
4. Rank images by semantic alignment
5. Select top image

Optional advanced stage:

* Pass top 3 images to a Vision LLM for final reranking

---

# 8 Narration Agent

Use:

* Latest Qwen TTS

Responsibilities:

* Convert full script to natural speech
* Maintain pacing
* Ensure clarity and pronunciation

---

# 9 Timeline Synchronization Agent
## Use the current code in the /moviepy_starter directory, it includes most of the code for this step.
Purpose:

* Align visuals with narration timing

Process:

* Measure duration of each script segment via TTS output
* Assign timestamps to corresponding images
* Maintain smooth pacing
* Optional:

  * Fade transitions
  * Cross dissolve
  * Subtle zoom effect

---

# 10 Video Assembly Module
Final Requirements:

* Resolution: **1280x720**
* Center images regardless of original resolution
* Maintain aspect ratio
* Background fill (blurred or black)
* Smooth transitions
* Export final MP4

---

# 🛠 Model & Tool Integrations

* LLM Inference: Groq / Cerebras (use groq where we have to make decision based on smaller data because its api provides very little context and use Cerebras where need to do things with bigger data like writing the whole script.)
* TTS: Latest Qwen TTS
* Website Discovery: DDGS
* Image Search: DDGS
* Crawling: crawl4ai
* Image–Text Matching: OpenCLIP ViT-B/16
* Orchestration: CrewAI multi-agent workflow
* Caching: Agentic multi-layer cache

---

# 🧩 Final System Flow

```
User Topic
   ↓
Narrative Architect
   ↓
DDGS Website Discovery
   ↓
crawl4ai Scraping
   ↓
RAG Retrieval
   ↓
Script Writer
   ↓
Image Placement Agent
   ↓
Segment → LLM Dual Output:
      - Search Queries
      - Visual Description
   ↓
DDGS Image Retrieval
   ↓
OpenCLIP Ranking
   ↓
Best Image Selected
   ↓
Qwen TTS
   ↓
Timeline Sync
   ↓
Video Assembly (1280x720)
```

---

This is now:

* Structurally clean
* Computationally efficient
* Semantically optimized
* Production-grade architecture

If you want next, we can convert this into:

* CrewAI agent definitions
* A task dependency graph
* Or a lean version optimized for low-resource machines (like your 16GB system).
