"""Video Assembly Service.

This module handles the final video production:
1. Timeline building - Creates time-ordered segment list
2. Video rendering - Assembles images + audio into MP4
3. Visual effects - Zoom animation with black letterboxing

Uses MoviePy for video manipulation with PIL for image processing.
"""

import math
import os
from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)
from PIL import Image

from core.models import create_timeline_item


def zoom_in_effect(clip, zoom_ratio=0.04):
    """Apply smooth zoom-in effect using PIL for high-quality resizing.

    Creates a Ken Burns effect by slowly zooming into the image over time.
    Uses PIL for high-quality Lanczos resizing.

    Args:
        clip: MoviePy video clip
        zoom_ratio: Zoom speed (0.04 = 4% zoom per second)

    Returns:
        Transformed clip with zoom effect
    """

    def effect(get_frame, t):
        return _apply_zoom_frame(get_frame(t), zoom_ratio, t)

    return clip.transform(effect)


def _apply_zoom_frame(frame, zoom_ratio, time_seconds):
    """Apply zoom transformation to a single video frame.

    This is the inner function that does the actual zoom processing:
    1. Convert frame to PIL Image
    2. Calculate zoomed size based on time
    3. Resize up (zoom in)
    4. Crop to original size (pan center)
    5. Resize back down to maintain frame size
    6. Convert back to numpy array

    Args:
        frame: Video frame as numpy array
        zoom_ratio: Zoom speed
        time_seconds: Current time in video

    Returns:
        Transformed frame as numpy array
    """
    img = Image.fromarray(frame)
    base_size = img.size

    # Calculate new size with zoom
    new_size = [
        math.ceil(img.size[0] * (1 + (zoom_ratio * time_seconds))),
        math.ceil(img.size[1] * (1 + (zoom_ratio * time_seconds))),
    ]

    # Ensure even dimensions for video codec compatibility
    new_size[0] = new_size[0] + (new_size[0] % 2)
    new_size[1] = new_size[1] + (new_size[1] % 2)

    # High-quality resize up (zoom in)
    img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Crop back to original size (center crop for zoom effect)
    x = math.ceil((new_size[0] - base_size[0]) / 2)
    y = math.ceil((new_size[1] - base_size[1]) / 2)
    img = img.crop((x, y, new_size[0] - x, new_size[1] - y)).resize(
        base_size, Image.Resampling.LANCZOS
    )

    result = np.array(img)
    img.close()

    return result


def build_timeline(segments):
    """Build a timeline from script segments.

    Converts segments with images and audio into a time-ordered list
    with precise timing. Duration is determined by audio file length.

    Args:
        segments: List of segment dicts with image and audio paths

    Returns:
        List of timeline item dicts with timing info

    Raises:
        RuntimeError: If audio file cannot be loaded
    """
    print(f"[TIMELINE] Building timeline from {len(segments)} segments", flush=True)
    timeline = []
    cursor = 0.0  # Current timestamp

    for segment in segments:
        selected_image = segment.get("selected_image_path")
        narration_audio = segment.get("narration_audio_path")

        # Skip segments missing required files
        if selected_image is None or narration_audio is None:
            print(
                f"[TIMELINE] Segment {segment['segment_id']}: missing image/audio, skipped",
                flush=True,
            )
            continue

        if not selected_image.exists() or not narration_audio.exists():
            print(
                f"[TIMELINE] Segment {segment['segment_id']}: missing files on disk, skipped",
                flush=True,
            )
            continue

        # Get duration from audio file
        try:
            with AudioFileClip(str(narration_audio)) as audio_clip:
                duration = float(audio_clip.duration)
        except Exception as e:
            raise RuntimeError(f"Failed to load audio file: {narration_audio}: {e}")

        segment["duration_seconds"] = duration
        timeline.append(
            create_timeline_item(
                segment_id=segment["segment_id"],
                text=segment["text"],
                start_seconds=cursor,
                end_seconds=cursor + duration,
                duration_seconds=duration,
                image_path=selected_image,
                audio_path=narration_audio,
            )
        )
        cursor += duration
        print(
            f"[TIMELINE] Segment {segment['segment_id']}: duration={duration:.2f}s start={timeline[-1]['start_seconds']:.2f}s",
            flush=True,
        )
    print(f"[TIMELINE] Timeline ready with {len(timeline)} items", flush=True)
    return timeline


def assemble_video(
    timeline,
    output_path,
    resolution=(1280, 720),
    fps=10,
    transition_seconds=0.3,
    zoom_strength=3.0,
):
    """Assemble final video from timeline items.

    For each timeline item:
    1. Create black background
    2. Create foreground image (centered, zoom effect)
    3. Composite with audio
    4. Concatenate all clips

    Args:
        timeline: List of timeline item dicts
        output_path: Output MP4 file path
        resolution: Video resolution (width, height)
        fps: Frames per second
        transition_seconds: Overlap between clips
        zoom_strength: Zoom effect intensity (0 to disable)

    Returns:
        Path to generated video file
    """
    if not timeline:
        raise ValueError("Timeline is empty; cannot assemble video.")

    print(
        f"[VIDEO] Rendering video with {len(timeline)} clips -> {output_path}",
        flush=True,
    )

    clips = []
    try:
        for item in timeline:
            print(
                f"[VIDEO] Building clip for segment {item['segment_id']} ({item['duration_seconds']:.2f}s)",
                flush=True,
            )
            clip = _build_segment_clip(
                item,
                resolution=resolution,
                fps=fps,
                zoom_strength=zoom_strength,
            )
            clips.append(clip)

        # Concatenate with small negative padding for smooth transitions
        final_clip = concatenate_videoclips(
            clips,
            method="compose",
            padding=-transition_seconds,
        )

        final_duration = final_clip.duration

        # Render final video
        final_clip.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            threads=os.cpu_count(),
            logger="bar",
        )
        final_clip.close()
        print(f"[VIDEO] Render complete: {output_path}", flush=True)
    finally:
        for clip in clips:
            clip.close()

    return output_path


def _build_segment_clip(
    item,
    resolution,
    fps,
    zoom_strength,
):
    """Build a single segment video clip.

    Creates a composited clip with:
    - Black background (letterboxing)
    - Foreground image (centered, with zoom effect)
    - Audio track

    Args:
        item: Timeline item dict
        resolution: Video resolution
        fps: Frames per second
        zoom_strength: Zoom intensity

    Returns:
        MoviePy CompositeVideoClip
    """
    width, height = resolution
    duration = max(0.1, item["duration_seconds"])

    # Create black background
    background = ColorClip(size=resolution, color=(0, 0, 0)).with_duration(duration)

    # Create foreground image
    foreground = (
        ImageClip(str(item["image_path"])).with_duration(duration).with_fps(fps)
    )
    # Fit image to frame (letterbox if needed)
    foreground = foreground.resized(height=height)
    if foreground.w > width:
        foreground = foreground.resized(width=width)

    # Apply zoom effect
    if zoom_strength > 0:
        foreground = zoom_in_effect(foreground, zoom_ratio=zoom_strength)

    foreground = foreground.with_position(("center", "center"))

    # Composite and add audio
    clips = [background, foreground]
    composite = CompositeVideoClip(clips, size=resolution).with_duration(duration)
    audio_clip = AudioFileClip(str(item["audio_path"]))
    composite = composite.with_audio(audio_clip)
    return composite

    with Image.open(source_image_path).convert("RGB"):
        fitted = ImageOps.fit(
            source_image_path, resolution, method=Image.Resampling.LANCZOS
        )
        blurred = fitted.filter(ImageFilter.GaussianBlur(28))
        blurred.save(out_path, format="JPEG", quality=90)
    return out_path

    with Image.open(source_image_path).convert("RGB") as source:
        fitted = ImageOps.fit(source, resolution, method=Image.Resampling.LANCZOS)
        blurred = fitted.filter(ImageFilter.GaussianBlur(28))
        blurred.save(out_path, format="JPEG", quality=90)
    return out_path
