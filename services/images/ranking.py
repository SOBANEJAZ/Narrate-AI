"""Image ranking agent."""

import re

import cv2
import numpy as np
import open_clip
import torch
from PIL import Image

from core.text_utils import extract_keywords


def create_ranking_state(model_name="ViT-B-16", pretrained_name="laion2b_s34b_b88k"):
    """Create image ranking state and initialize CLIP."""
    state = {
        "model_name": model_name,
        "pretrained_name": pretrained_name,
        "clip_ready": False,
        "clip_model": None,
        "clip_preprocess": None,
        "clip_tokenizer": None,
        "device": "cpu",
    }

    state["device"] = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name,
        pretrained=pretrained_name,
    )
    model = model.to(state["device"])
    model.eval()
    tokenizer = open_clip.get_tokenizer(model_name)
    state["clip_model"] = model
    state["clip_preprocess"] = preprocess
    state["clip_tokenizer"] = tokenizer
    state["clip_ready"] = True
    print(f"[RANK] OpenCLIP ready on device: {state['device']}", flush=True)

    return state


def rank_images(state, segments):
    """Rank images for all segments."""
    print(f"[RANK] Ranking images for {len(segments)} segments", flush=True)
    for segment in segments:
        candidates = segment.get("candidate_images", [])
        if not candidates:
            print(
                f"[RANK] Segment {segment['segment_id']}: no candidates to rank",
                flush=True,
            )
            continue
        _rank_with_clip(state, segment)

        winner = max(candidates, key=lambda candidate: candidate.get("score", 0.0))
        segment["selected_image_path"] = winner.get("local_path")
        print(
            f"[RANK] Segment {segment['segment_id']}: selected image (score={winner.get('score', 0.0):.4f})",
            flush=True,
        )
    return segments


def _calculate_quality_score(image):
    """Calculate quality score for an image (0-1 scale)."""
    try:
        width, height = image.size
        pixel_count = width * height

        # Resolution score (higher = better)
        max_pixels = 4000 * 4000  # 16MP
        resolution_score = min(pixel_count / max_pixels, 1.0)

        # Sharpness score using Laplacian variance (lower = blurrier)
        gray = image.convert("L")
        np_image = np.array(gray)
        laplacian_var = (
            cv2.Laplacian(np_image, cv2.CV_64F).var() if cv2 else np.var(np_image)
        )

        # Normalize sharpness score (empirical thresholds)
        sharpness_score = min(max((laplacian_var - 50) / 200, 0), 1.0)  # Clip to 0-1

        # Combined quality score (weight resolution more heavily)
        quality_score = 0.6 * resolution_score + 0.4 * sharpness_score

        # Penalize very low resolution or extremely blurry images
        if pixel_count < 160000 or laplacian_var < 50:  # 400x400 = 160000
            quality_score *= 0.3

        return quality_score
    except Exception:
        return 0.1  # Low quality if any error occurs


def _rank_with_clip(state, segment):
    """Rank images using CLIP embeddings with quality filtering."""
    assert state["clip_model"] is not None
    assert state["clip_preprocess"] is not None
    assert state["clip_tokenizer"] is not None

    visual_desc = segment.get("visual_description", "")
    valid_candidates = [
        candidate
        for candidate in segment.get("candidate_images", [])
        if candidate.get("local_path") is not None and candidate["local_path"].exists()
    ]
    if not valid_candidates:
        raise ValueError(
            f"No valid candidate images found for segment {segment['segment_id']}"
        )

    with torch.no_grad():
        text_tokens = state["clip_tokenizer"]([visual_desc]).to(state["device"])
        text_features = state["clip_model"].encode_text(text_tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        for candidate in valid_candidates:
            local_path = candidate["local_path"]
            if local_path is None or local_path.suffix.lower() == ".svg":
                continue

            try:
                image = Image.open(local_path).convert("RGB")

                # Calculate quality score
                quality_score = _calculate_quality_score(image)

                # Skip extremely low quality images
                if quality_score < 0.1:
                    candidate["score"] = 0.0
                    continue

                tensor = (
                    state["clip_preprocess"](image).unsqueeze(0).to(state["device"])
                )
                image_features = state["clip_model"].encode_image(tensor)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                similarity = float((image_features @ text_features.T).squeeze().item())

                # Combine CLIP similarity with quality score
                final_score = similarity * 0.7 + quality_score * 0.3
                candidate["score"] = final_score

            except Exception as e:
                print(f"[RANK] Error processing image {local_path}: {e}")
                candidate["score"] = 0.0
