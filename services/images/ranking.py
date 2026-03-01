"""Image Ranking Service using CLIP.

This module ranks candidate images using OpenCLIP (vision-language model):
1. Embeds the segment's search queries as text
2. Embeds each candidate image
3. Computes cosine similarity between text and image embeddings
4. Combines with image quality metrics (resolution, sharpness)
5. Selects highest-scoring image

CLIP (Contrastive Language-Image Pre-training) allows measuring
semantic similarity between images and text descriptions.
"""

import re

import cv2
import numpy as np
import open_clip
import torch
from PIL import Image

from core.text_utils import extract_keywords


def create_ranking_state(model_name="ViT-B-16", pretrained_name="laion2b_s34b_b88k"):
    """Create ranking state and initialize OpenCLIP model.

    OpenCLIP is a open-source version of CLIP that matches or exceeds
    original CLIP performance. Uses ViT-B-16 architecture with laion2b
    pretrained weights for strong visual-language understanding.

    Args:
        model_name: CLIP model architecture
        pretrained_name: Pretrained weight identifier

    Returns:
        State dict with model, preprocessing, tokenizer, and device
    """
    state = {
        "model_name": model_name,
        "pretrained_name": pretrained_name,
        "clip_ready": False,
        "clip_model": None,
        "clip_preprocess": None,
        "clip_tokenizer": None,
        "device": "cpu",
    }

    # Use GPU if available, otherwise CPU
    state["device"] = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name,
        pretrained=pretrained_name,
    )
    model = model.to(state["device"])
    model.eval()  # Inference mode
    tokenizer = open_clip.get_tokenizer(model_name)
    state["clip_model"] = model
    state["clip_preprocess"] = preprocess
    state["clip_tokenizer"] = tokenizer
    state["clip_ready"] = True
    print(f"[RANK] OpenCLIP ready on device: {state['device']}", flush=True)

    return state


def rank_images(state, segments):
    """Rank candidate images for all segments using CLIP.

    For each segment with candidate images:
    1. Rank using CLIP embeddings + quality scores
    2. Select highest-scoring image as the winner

    Args:
        state: Ranking state with CLIP model
        segments: List of segment dicts with candidate_images

    Returns:
        Segments with selected_image_path added
    """
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

        # Select best image
        winner = max(candidates, key=lambda candidate: candidate.get("score", 0.0))
        segment["selected_image_path"] = winner.get("local_path")
        print(
            f"[RANK] Segment {segment['segment_id']}: selected image (score={winner.get('score', 0.0):.4f})",
            flush=True,
        )
    return segments


def _calculate_quality_score(image):
    """Calculate image quality score (0-1 scale).

    Considers two factors:
    1. Resolution: Higher pixel count = better (up to 16MP)
    2. Sharpness: Higher Laplacian variance = sharper

    Combined with weighting (60% resolution, 40% sharpness).
    Penalizes very low resolution or extremely blurry images.

    Args:
        image: PIL Image to evaluate

    Returns:
        Quality score between 0 and 1
    """
    try:
        width, height = image.size
        pixel_count = width * height

        # Resolution score (higher = better)
        max_pixels = 4000 * 4000  # 16MP reference
        resolution_score = min(pixel_count / max_pixels, 1.0)

        # Sharpness score using Laplacian variance (lower = blurrier)
        gray = image.convert("L")
        np_image = np.array(gray)
        laplacian_var = (
            cv2.Laplacian(np_image, cv2.CV_64F).var() if cv2 else np.var(np_image)
        )

        # Normalize sharpness score (empirical thresholds)
        sharpness_score = min(max((laplacian_var - 50) / 200, 0), 1.0)

        # Combined quality score (weight resolution more heavily)
        quality_score = 0.6 * resolution_score + 0.4 * sharpness_score

        # Penalize very low resolution or extremely blurry images
        if pixel_count < 160000 or laplacian_var < 50:  # 400x400 = 160000
            quality_score *= 0.3

        return quality_score
    except Exception:
        return 0.1  # Low quality if any error occurs


def _rank_with_clip(state, segment):
    """Rank images using CLIP embeddings with quality filtering.

    Process:
    1. Tokenize segment's search queries as text embedding
    2. For each candidate image:
       a. Calculate quality score (resolution + sharpness)
       b. Skip if quality too low
       c. Encode image as embedding
       d. Compute cosine similarity with text
       e. Combine CLIP score (70%) + quality (30%)

    Args:
        state: Ranking state with CLIP model
        segment: Segment dict with candidate_images and search_queries
    """
    assert state["clip_model"] is not None
    assert state["clip_preprocess"] is not None
    assert state["clip_tokenizer"] is not None

    # Get ranking text from search queries or fall back to segment text
    search_queries = segment.get("search_queries", [])
    ranking_text = (
        " ".join(search_queries) if search_queries else segment.get("text", "")
    )

    # Filter to valid candidate images (have local path)
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
        # Encode ranking text
        text_tokens = state["clip_tokenizer"]([ranking_text]).to(state["device"])
        text_features = state["clip_model"].encode_text(text_tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        # Score each candidate image
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

                # Encode image
                tensor = (
                    state["clip_preprocess"](image).unsqueeze(0).to(state["device"])
                )
                image_features = state["clip_model"].encode_image(tensor)
                image_features /= image_features.norm(dim=-1, keepdim=True)

                # Cosine similarity
                similarity = float((image_features @ text_features.T).squeeze().item())

                # Combine CLIP similarity with quality score
                final_score = similarity * 0.7 + quality_score * 0.3
                candidate["score"] = final_score

            except Exception as e:
                print(f"[RANK] Error processing image {local_path}: {e}")
                candidate["score"] = 0.0
