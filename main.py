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


def check_and_reset_folder(folder_path):
    """Check if folder exists, clear it if it does, or create it if it doesn't."""
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
    else:
        try:
            os.makedirs(folder_path)
            print(f"Folder '{folder_path}' created successfully.")
        except OSError as e:
            print(f"Failed to create directory '{folder_path}': {e}")


def add_audio_to_video(video_path, audio_path, output_path):
    """Add audio to a video file and save the result."""
    with (
        VideoFileClip(video_path) as video_clip,
        AudioFileClip(audio_path) as audio_clip,
    ):
        video_with_audio = video_clip.with_audio(audio_clip)
        video_with_audio.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
        )


def delete_folder(folder_path):
    """Delete a folder and all its contents."""
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
            print(f"Folder '{folder_path}' deleted successfully.")
        except Exception as e:
            print(f"Failed to delete folder '{folder_path}': {e}")


def process_folders(folder_path):
    """Process all folders containing .webp images and .mp3 audio files."""
    all_clips = []
    size = (1920, 1080)

    for folder_name in os.listdir(folder_path):
        folder_full_path = os.path.join(folder_path, folder_name)
        if not os.path.isdir(folder_full_path):
            continue

        print(f"Processing folder: {folder_full_path}")
        without_audio_folder = os.path.join(folder_full_path, "without_audio")
        with_audio_folder = os.path.join(folder_full_path, "with_audio")
        check_and_reset_folder(without_audio_folder)
        check_and_reset_folder(with_audio_folder)

        for file_name in os.listdir(folder_full_path):
            file_full_path = os.path.join(folder_full_path, file_name)
            if not file_name.endswith(".webp"):
                continue

            audio_file = os.path.join(
                folder_full_path, file_name.split(".")[0] + ".mp3"
            )
            if not os.path.exists(audio_file):
                print(f"No audio file found for {file_name}")
                continue

            with AudioFileClip(audio_file) as audio_clip:
                audio_duration = audio_clip.duration

            # Create image clip with zoom-in effect
            slide = (
                ImageClip(file_full_path)
                .with_fps(25)
                .with_duration(audio_duration)
                .with_size(size)
            )
            # Apply zoom effect using time-based resize
            slide = slide.resized(lambda t: 1 + 0.04 * t)
            slide = slide.with_position(("center", "center"))
            slide = CompositeVideoClip([slide], size=size)

            without_audio_output = os.path.join(
                without_audio_folder, file_name.split(".")[0] + ".mp4"
            )
            slide.write_videofile(without_audio_output)

            with_audio_output = os.path.join(
                with_audio_folder, file_name.split(".")[0] + ".mp4"
            )
            add_audio_to_video(without_audio_output, audio_file, with_audio_output)

            # Store clip for concatenation
            all_clips.append(VideoFileClip(with_audio_output))

    # Concatenate all video clips
    if all_clips:
        final_clip = concatenate_videoclips(all_clips)
        final_output_path = os.path.join(folder_path, "final_output.mp4")
        final_clip.write_videofile(
            final_output_path, codec="libx264", audio_codec="aac"
        )
        final_clip.close()

        # Close all individual clips
        for clip in all_clips:
            clip.close()

    # Cleanup: Delete intermediate folders
    for folder_name in os.listdir(folder_path):
        folder_full_path = os.path.join(folder_path, folder_name)
        if os.path.isdir(folder_full_path):
            without_audio_folder = os.path.join(folder_full_path, "without_audio")
            with_audio_folder = os.path.join(folder_full_path, "with_audio")
            delete_folder(without_audio_folder)
            delete_folder(with_audio_folder)


if __name__ == "__main__":
    process_folders("files")
