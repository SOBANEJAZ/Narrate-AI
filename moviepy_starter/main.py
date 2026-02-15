from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from narrate_ai.models import ScriptSegment
from narrate_ai.video import assemble_video, build_timeline


IMAGE_EXTENSIONS = {".webp", ".png", ".jpg", ".jpeg"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac"}


def process_folders(folder_path: str | Path) -> Path:
    """
    Assemble pre-existing segment assets into a final slideshow video.

    Expected layout:
    files/
      1/
        1.webp
        1.mp3
      2/
        2.webp
        2.mp3
      ...
    """
    root = Path(folder_path)
    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")

    segments: list[ScriptSegment] = []
    segment_folders = sorted(
        [p for p in root.iterdir() if p.is_dir()],
        key=lambda path: int(path.name) if path.name.isdigit() else path.name,
    )
    for index, folder in enumerate(segment_folders, start=1):
        images = sorted(
            [p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS]
        )
        audios = sorted(
            [p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS]
        )
        if not images or not audios:
            continue

        segments.append(
            ScriptSegment(
                segment_id=index,
                text=f"Segment {folder.name}",
                start_sentence=index,
                end_sentence=index,
                selected_image_path=images[0],
                narration_audio_path=audios[0],
            )
        )

    timeline = build_timeline(segments)
    if not timeline:
        raise RuntimeError(f"No valid image/audio segment pairs found in {root}.")

    output_path = root / "final_output.mp4"
    assemble_video(
        timeline,
        output_path,
        resolution=(1280, 720),
        fps=15,
        transition_seconds=0.3,
        zoom_strength=0.08,
        background_mode="black",
    )
    return output_path


if __name__ == "__main__":
    input_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("files")
    output = process_folders(input_root)
    print(f"Final video written: {output}")
