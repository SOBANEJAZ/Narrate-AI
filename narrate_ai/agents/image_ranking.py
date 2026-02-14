"""Image ranking agent using functional programming style."""

import re

from ..text_utils import extract_keywords

try:
    import torch
except Exception:
    torch = None

try:
    import open_clip
except Exception:
    open_clip = None

try:
    from PIL import Image
except Exception:
    Image = None


def create_ranking_state(model_name="ViT-L-14", pretrained_name="laion2b_s32b_b82k"):
    """Create image ranking state and initialize CLIP if available."""
    state = {
        "model_name": model_name,
        "pretrained_name": pretrained_name,
        "clip_ready": False,
        "clip_model": None,
        "clip_preprocess": None,
        "clip_tokenizer": None,
        "device": "cpu",
    }

    if torch is None or open_clip is None or Image is None:
        print(
            "[RANK] OpenCLIP unavailable; using keyword-overlap fallback",
            flush=True,
        )
        return state

    try:
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
    except Exception:
        state["clip_ready"] = False
        print(
            "[RANK] OpenCLIP initialization failed; using fallback ranker",
            flush=True,
        )

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
        if state["clip_ready"]:
            _rank_with_clip(state, segment)
        else:
            _rank_with_text_overlap(segment)

        winner = max(candidates, key=lambda candidate: candidate.get("score", 0.0))
        segment["selected_image_path"] = winner.get("local_path")
        print(
            f"[RANK] Segment {segment['segment_id']}: selected image (score={winner.get('score', 0.0):.4f})",
            flush=True,
        )
    return segments


def _rank_with_clip(state, segment):
    """Rank images using CLIP embeddings."""
    assert state["clip_model"] is not None
    assert state["clip_preprocess"] is not None
    assert state["clip_tokenizer"] is not None
    assert torch is not None
    assert Image is not None

    visual_desc = segment.get("visual_description", "")
    valid_candidates = [
        candidate
        for candidate in segment.get("candidate_images", [])
        if candidate.get("local_path") is not None and candidate["local_path"].exists()
    ]
    if not valid_candidates:
        _rank_with_text_overlap(segment)
        return

    with torch.no_grad():
        text_tokens = state["clip_tokenizer"]([visual_desc]).to(state["device"])
        text_features = state["clip_model"].encode_text(text_tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        for candidate in valid_candidates:
            try:
                local_path = candidate["local_path"]
                if local_path is None:
                    continue
                image = Image.open(local_path).convert("RGB")
                tensor = (
                    state["clip_preprocess"](image).unsqueeze(0).to(state["device"])
                )
                image_features = state["clip_model"].encode_image(tensor)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                similarity = float((image_features @ text_features.T).squeeze().item())
                candidate["score"] = similarity
            except Exception:
                candidate["score"] = _fallback_score(visual_desc, candidate)


def _rank_with_text_overlap(segment):
    """Rank images using keyword overlap as fallback."""
    visual_desc = segment.get("visual_description", "")
    for candidate in segment.get("candidate_images", []):
        candidate["score"] = _fallback_score(visual_desc, candidate)


def _fallback_score(text, candidate):
    """Calculate score based on keyword overlap."""
    keywords = set(extract_keywords(text, limit=12))
    candidate_text = (
        f"{candidate['title']} {candidate['source']} {candidate['url']}".lower()
    )
    tokenized = set(re.findall(r"[a-z0-9'-]+", candidate_text))
    overlap = len(keywords & tokenized)
    return float(overlap)
