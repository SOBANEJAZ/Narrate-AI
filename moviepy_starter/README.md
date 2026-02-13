# MoviePy Starter (Step 9 + 10)

This module assembles pre-existing segment assets into a final slideshow video.

## Expected Input

```
files/
  1/
    1.webp
    1.mp3
  2/
    2.webp
    2.mp3
  ...
```

Each numbered folder should contain at least one image and one audio file.

Supported image types: `.webp`, `.png`, `.jpg`, `.jpeg`  
Supported audio types: `.mp3`, `.wav`, `.m4a`, `.aac`

## Output Behavior

- Produces `1280x720` MP4
- Centers images regardless of source resolution
- Preserves aspect ratio
- Uses black background fill
- Applies subtle zoom + smooth transition timing

## Usage

```bash
python moviepy_starter/main.py moviepy_starter/files
```

Output:

```
files/final_output.mp4
```
