from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import ImageCandidate, ScriptSegment
from ..text_utils import extract_keywords

try:
    import torch
except Exception:  # pragma: no cover - optional dependency fallback
    torch = None  # type: ignore[assignment]

try:
    import open_clip
except Exception:  # pragma: no cover - optional dependency fallback
    open_clip = None  # type: ignore[assignment]

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency fallback
    Image = None  # type: ignore[assignment]


@dataclass(slots=True)
class ImageRankingAgent:
    model_name: str = "ViT-B-16"
    pretrained_name: str = "laion2b_s34b_b88k"
    _clip_ready: bool = field(default=False, init=False)
    _clip_model: object | None = field(default=None, init=False)
    _clip_preprocess: object | None = field(default=None, init=False)
    _clip_tokenizer: object | None = field(default=None, init=False)
    _device: str = field(default="cpu", init=False)

    def __post_init__(self) -> None:
        if torch is None or open_clip is None or Image is None:
            print("[RANK] OpenCLIP unavailable; using keyword-overlap fallback", flush=True)
            return
        try:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            model, _, preprocess = open_clip.create_model_and_transforms(
                self.model_name,
                pretrained=self.pretrained_name,
            )
            model = model.to(self._device)
            model.eval()
            tokenizer = open_clip.get_tokenizer(self.model_name)
            self._clip_model = model
            self._clip_preprocess = preprocess
            self._clip_tokenizer = tokenizer
            self._clip_ready = True
            print(f"[RANK] OpenCLIP ready on device: {self._device}", flush=True)
        except Exception:
            self._clip_ready = False
            print("[RANK] OpenCLIP initialization failed; using fallback ranker", flush=True)

    def rank(self, segments: list[ScriptSegment]) -> list[ScriptSegment]:
        print(f"[RANK] Ranking images for {len(segments)} segments", flush=True)
        for segment in segments:
            if not segment.candidate_images:
                print(f"[RANK] Segment {segment.segment_id}: no candidates to rank", flush=True)
                continue
            if self._clip_ready:
                self._rank_with_clip(segment)
            else:
                self._rank_with_text_overlap(segment)

            winner = max(segment.candidate_images, key=lambda candidate: candidate.score)
            segment.selected_image_path = winner.local_path
            print(
                f"[RANK] Segment {segment.segment_id}: selected image (score={winner.score:.4f})",
                flush=True,
            )
        return segments

    def _rank_with_clip(self, segment: ScriptSegment) -> None:
        assert self._clip_model is not None
        assert self._clip_preprocess is not None
        assert self._clip_tokenizer is not None
        assert torch is not None
        assert Image is not None

        valid_candidates = [
            candidate
            for candidate in segment.candidate_images
            if candidate.local_path is not None and candidate.local_path.exists()
        ]
        if not valid_candidates:
            self._rank_with_text_overlap(segment)
            return

        with torch.no_grad():
            text_tokens = self._clip_tokenizer([segment.visual_description]).to(self._device)
            text_features = self._clip_model.encode_text(text_tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)

            for candidate in valid_candidates:
                try:
                    image = Image.open(candidate.local_path).convert("RGB")
                    tensor = self._clip_preprocess(image).unsqueeze(0).to(self._device)
                    image_features = self._clip_model.encode_image(tensor)
                    image_features /= image_features.norm(dim=-1, keepdim=True)
                    similarity = float((image_features @ text_features.T).squeeze().item())
                    candidate.score = similarity
                except Exception:
                    candidate.score = self._fallback_score(segment.visual_description, candidate)

    def _rank_with_text_overlap(self, segment: ScriptSegment) -> None:
        for candidate in segment.candidate_images:
            candidate.score = self._fallback_score(segment.visual_description, candidate)

    def _fallback_score(self, text: str, candidate: ImageCandidate) -> float:
        keywords = set(extract_keywords(text, limit=12))
        candidate_text = f"{candidate.title} {candidate.source} {candidate.url}".lower()
        tokenized = set(re.findall(r"[a-z0-9'-]+", candidate_text))
        overlap = len(keywords & tokenized)
        return float(overlap)
