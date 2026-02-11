# AGENTS.md - AI Coding Assistant Guidelines

## Project Overview

Images-to-Video Converter - A Python script that converts images (.webp) with matching audio files (.mp3) into video files with zoom-in effects.

## Build/Lint/Test Commands

Since this project has no formal build system configured, use these standard Python commands:

### Running the Application
```bash
python main.py
```

### Code Quality (Suggested Setup)
```bash
# Install linting/formatting tools
pip install black flake8 pylint mypy pytest

# Format code
black main.py

# Lint code
flake8 main.py
pylint main.py

# Type checking
mypy main.py

# Run tests (if tests/ directory exists)
pytest

# Run single test
pytest tests/test_specific.py::test_function_name -v
```

### Virtual Environment
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install moviepy
```

## Code Style Guidelines

### Imports
- Group imports: standard library, third-party, local
- Use absolute imports
- Import from `moviepy` directly (v2.x style) instead of `moviepy.editor`
- Example from main.py:
```python
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    ImageClip,
    vfx,
)
import os
import shutil
```

### Formatting
- 4 spaces for indentation
- 2 blank lines between top-level functions
- 1 blank line between methods in a class
- Max line length: 88 characters (Black default) or 100
- Use double quotes for strings

### Naming Conventions
- Functions: `snake_case` (e.g., `add_audio_to_video`)
- Variables: `snake_case` (e.g., `folder_path`, `audio_clip`)
- Constants: `UPPER_SNAKE_CASE`
- Files: `snake_case.py`

### Type Hints
While not currently used, prefer adding type hints for function signatures:
```python
def add_audio_to_video(video_path: str, audio_path: str, output_path: str) -> None:
    ...
```

### Resource Management (Critical for MoviePy v2.x)
- **Always use context managers** (`with` statement) for `VideoFileClip` and `AudioFileClip` to ensure proper resource cleanup
- This prevents memory leaks and file handle issues, especially on Windows
- Example:
```python
with VideoFileClip(video_path) as video, AudioFileClip(audio_path) as audio:
    video_with_audio = video.with_audio(audio)
    video_with_audio.write_videofile(output_path)
# Clips are automatically closed when exiting the 'with' block
```
- When not using context managers, always call `.close()` on clips when done

### Error Handling
- Use try-except blocks for file operations and external library calls
- Print informative error messages
- Example pattern from main.py:
```python
try:
    os.makedirs(folder_path)
    print(f"Folder '{folder_path}' created successfully.")
except OSError as e:
    print(f"Failed to create directory '{folder_path}': {e}")
```

### Documentation
- Use docstrings for functions (Google style or NumPy style)
- Keep inline comments minimal and meaningful
- Document complex video processing logic

## Project Structure

```
.
├── main.py              # Main application entry point
├── files/               # Input/output directory
│   ├── 1/
│   │   ├── 1.webp      # Image file
│   │   └── 1.mp3       # Audio file
│   ├── 2/
│   └── ...
└── README.md
```

## Dependencies

- **moviepy**: Video editing library (v2.2.1+)
- **ffmpeg**: Required by moviepy (system dependency)

## Key Implementation Notes

1. **Image Processing**: Uses `ImageClip` with zoom-in effect using `resized(lambda t: 1 + 0.04 * t)`
2. **API Migration (v2.x)**: Updated from deprecated methods to new `with_*` methods:
   - `.set_duration()` → `.with_duration()`
   - `.set_fps()` → `.with_fps()`
   - `.resize()` → `.with_size()` or `.resized()`
   - `.set_audio()` → `.with_audio()`
   - `.set_position()` → `.with_position()`
3. **Video Resolution**: Fixed at 1920x1080 (1080p)
4. **Frame Rate**: 25 FPS
5. **Output Format**: MP4 with libx264 codec and AAC audio
6. **Workflow**: Creates intermediate files in `without_audio/` and `with_audio/` folders, then concatenates

## Testing Recommendations

When adding tests, create a `tests/` directory with:
- Unit tests for each function
- Integration tests with small sample files
- Mock moviepy calls to avoid actual video processing in tests

## Git Workflow

- Check `.gitattributes` for line ending normalization
- No CI/CD configured currently
