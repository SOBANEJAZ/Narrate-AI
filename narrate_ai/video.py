"""Video assembly module using functional programming style."""

from pathlib import Path

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)

from .models import create_timeline_item
from .text_utils import safe_filename

try:
    from PIL import Image, ImageFilter, ImageOps
except Exception:
    Image = None
    ImageFilter = None
    ImageOps = None


def build_timeline(segments):
    """Build a timeline from script segments."""
    print(f"[TIMELINE] Building timeline from {len(segments)} segments", flush=True)
    timeline = []
    cursor = 0.0

    for segment in segments:
        selected_image = segment.get("selected_image_path")
        narration_audio = segment.get("narration_audio_path")

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

        try:
            with AudioFileClip(str(narration_audio)) as audio_clip:
                duration = float(audio_clip.duration)
        except Exception:
            duration = max(3.0, segment.get("duration_seconds", 3.0))

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
    fps=24,
    transition_seconds=0.3,
    zoom_strength=0.04,
    background_mode="black",
):
    """Assemble video from timeline items."""
    if not timeline:
        raise ValueError("Timeline is empty; cannot assemble video.")

    print(
        f"[VIDEO] Rendering video with {len(timeline)} clips -> {output_path}",
        flush=True,
    )
    render_cache_dir = output_path.parent / "_render_cache"
    render_cache_dir.mkdir(parents=True, exist_ok=True)

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
                background_mode=background_mode,
                render_cache_dir=render_cache_dir,
            )
            clips.append(clip)

        final_clip = concatenate_videoclips(
            clips, method="compose", padding=-max(0.0, transition_seconds)
        )
        final_clip.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
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
    background_mode,
    render_cache_dir,
):
    """Build a single segment clip."""
    width, height = resolution
    duration = max(0.1, item["duration_seconds"])

    background = _background_clip(
        item["image_path"],
        duration=duration,
        resolution=resolution,
        background_mode=background_mode,
        render_cache_dir=render_cache_dir,
    )

    foreground = (
        ImageClip(str(item["image_path"])).with_duration(duration).with_fps(fps)
    )
    foreground = foreground.resized(height=height)
    if foreground.w > width:
        foreground = foreground.resized(width=width)

    if zoom_strength > 0:
        foreground = foreground.resized(
            lambda t: 1.0 + (zoom_strength * (t / duration))
        )

    foreground = foreground.with_position(("center", "center"))
    composite = CompositeVideoClip(
        [background, foreground], size=resolution
    ).with_duration(duration)
    audio_clip = AudioFileClip(str(item["audio_path"]))
    composite = composite.with_audio(audio_clip)
    return composite


def _background_clip(
    image_path,
    duration,
    resolution,
    background_mode,
    render_cache_dir,
):
    """Create a background clip for a segment."""
    if background_mode == "blur":
        blurred_path = _build_blurred_image(image_path, resolution, render_cache_dir)
        if blurred_path is not None:
            return ImageClip(str(blurred_path)).with_duration(duration)

    return ColorClip(size=resolution, color=(0, 0, 0)).with_duration(duration)


def _build_blurred_image(
    source_image_path,
    resolution,
    render_cache_dir,
):
    """Build a blurred background image."""
    if Image is None or ImageOps is None or ImageFilter is None:
        return None

    safe_stem = safe_filename(source_image_path.stem, max_length=80)
    out_path = render_cache_dir / f"blur_{safe_stem}.jpg"
    if out_path.exists():
        return out_path

    try:
        with Image.open(source_image_path).convert("RGB") as source:
            fitted = ImageOps.fit(source, resolution, method=Image.Resampling.LANCZOS)
            blurred = fitted.filter(ImageFilter.GaussianBlur(28))
            blurred.save(out_path, format="JPEG", quality=90)
        return out_path
    except Exception:
        return None
