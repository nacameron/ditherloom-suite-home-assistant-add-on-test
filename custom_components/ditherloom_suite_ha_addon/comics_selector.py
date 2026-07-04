from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from PIL import Image

from .xkcd_provider import analyze_xkcd_image


@dataclass(frozen=True)
class ComicCandidate:
    source_id: str
    source_name: str
    title: str
    source_url: str
    image_url: str
    image: Image.Image
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ComicSuitability:
    suitable: bool
    score: int
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    panel_count: int
    aspect_ratio: float
    saturated_pixel_ratio: float
    safe_colour_pixel_ratio: float
    poor_colour_pixel_ratio: float
    dominant_poor_colour_families: tuple[str, ...]
    black_pixel_ratio: float
    ink_pixel_ratio: float
    small_detail_pixel_ratio: float
    fitted_art_size: tuple[int, int]
    supported_features: tuple[str, ...] = field(default_factory=tuple)
    unsupported_features: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ComicSelection:
    candidate: ComicCandidate
    suitability: ComicSuitability
    rejected: tuple[dict[str, Any], ...] = field(default_factory=tuple)


Analyzer = Callable[[Image.Image], ComicSuitability]


def analyze_comic_image(image: Image.Image) -> ComicSuitability:
    suitability = analyze_xkcd_image(image)
    return ComicSuitability(
        suitable=suitability.suitable,
        score=suitability.score,
        reasons=tuple(suitability.reasons),
        warnings=tuple(suitability.warnings),
        panel_count=suitability.panel_count,
        aspect_ratio=suitability.aspect_ratio,
        saturated_pixel_ratio=suitability.saturated_pixel_ratio,
        safe_colour_pixel_ratio=suitability.safe_colour_pixel_ratio,
        poor_colour_pixel_ratio=suitability.poor_colour_pixel_ratio,
        dominant_poor_colour_families=tuple(suitability.dominant_poor_colour_families),
        black_pixel_ratio=suitability.black_pixel_ratio,
        ink_pixel_ratio=suitability.ink_pixel_ratio,
        small_detail_pixel_ratio=suitability.small_detail_pixel_ratio,
        fitted_art_size=tuple(suitability.fitted_art_size),
        supported_features=tuple(suitability.supported_features),
        unsupported_features=tuple(suitability.unsupported_features),
    )


def select_best_comic_candidate(
    candidates: Iterable[ComicCandidate],
    *,
    analyzer: Analyzer = analyze_comic_image,
) -> ComicSelection:
    best: tuple[ComicCandidate, ComicSuitability] | None = None
    rejected: list[dict[str, Any]] = []
    for candidate in candidates:
        suitability = analyzer(candidate.image)
        if suitability.suitable:
            return ComicSelection(candidate=candidate, suitability=suitability, rejected=tuple(rejected))
        rejected.append(_rejection_metadata(candidate, suitability))
        if best is None or suitability.score > best[1].score:
            best = (candidate, suitability)
    if best is None:
        raise ValueError("No comic candidates were supplied")
    return ComicSelection(candidate=best[0], suitability=best[1], rejected=tuple(rejected))


def comic_suitability_metadata(suitability: ComicSuitability) -> dict[str, Any]:
    return {
        "suitable": suitability.suitable,
        "score": suitability.score,
        "reasons": list(suitability.reasons),
        "warnings": list(suitability.warnings),
        "panel_count": suitability.panel_count,
        "aspect_ratio": suitability.aspect_ratio,
        "saturated_pixel_ratio": suitability.saturated_pixel_ratio,
        "safe_colour_pixel_ratio": suitability.safe_colour_pixel_ratio,
        "poor_colour_pixel_ratio": suitability.poor_colour_pixel_ratio,
        "dominant_poor_colour_families": list(suitability.dominant_poor_colour_families),
        "black_pixel_ratio": suitability.black_pixel_ratio,
        "ink_pixel_ratio": suitability.ink_pixel_ratio,
        "small_detail_pixel_ratio": suitability.small_detail_pixel_ratio,
        "fitted_art_size": list(suitability.fitted_art_size),
        "supported_features": list(suitability.supported_features),
        "unsupported_features": list(suitability.unsupported_features),
    }


def _rejection_metadata(candidate: ComicCandidate, suitability: ComicSuitability) -> dict[str, Any]:
    return {
        "source_id": candidate.source_id,
        "title": candidate.title,
        "source_url": candidate.source_url,
        "score": suitability.score,
        "reasons": list(suitability.reasons),
        "warnings": list(suitability.warnings),
    }
