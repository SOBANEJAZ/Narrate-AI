# MoviePy Starter Code

This directory contains the starter code for timeline synchronization (Step 9) of the automated documentary generation system.

## Overview

This code handles the timeline synchronization and video assembly aspects of the documentary generation pipeline:

- Processes folders containing `.webp` images and `.mp3` audio files
- Creates video clips from images with zoom effects
- Adds audio to video clips
- Concatenates all clips into a final output
- Manages temporary files and cleanup

## Files Structure

The code expects the following structure:
```
files/
├── 1/
│   ├── image1.webp
│   ├── image1.mp3
│   ├── image2.webp
│   └── image2.mp3
├── 2/
│   ├── ...
```

Each numbered folder represents a segment of the documentary with corresponding image and audio files.

## Usage

Run the script to process all folders in the `files/` directory:

```bash
python main.py
```

The script will:
1. Process each folder containing `.webp` images and `.mp3` audio files
2. Create intermediate videos with zoom effects
3. Combine audio and video
4. Concatenate all segments into a final output
5. Clean up temporary files