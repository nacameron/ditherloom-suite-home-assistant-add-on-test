from __future__ import annotations

import json
import math
import random
import urllib.request
from colorsys import rgb_to_hsv
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from .renderer.pack import RenderArtifact, render_to_artifact, write_artifact
from .renderer.palette import PACKET_RGB, TEMPLATE_COLOURS, ordered_code

XKCD_LICENSE = "CC BY-NC 2.5"
XKCD_LICENSE_URL = "https://creativecommons.org/licenses/by-nc/2.5/"
XKCD_SOURCE_NAME = "xkcd"
XKCD_ATTRIBUTION = "xkcd / Randall Munroe"
XKCD_API_CURRENT = "https://xkcd.com/info.0.json"
XKCD_API_BY_NUMBER = "https://xkcd.com/{num}/info.0.json"
PROVIDER_ID = "xkcd_comic"
PROVIDER_NAME = "xkcd Comic"
DEFAULT_RANDOM_ATTEMPTS = 30

WIDTH = 400
HEIGHT = 300
ART_BOX = (12, 42, 388, 260)
TITLE_BOX = (12, 8, 388, 36)
ATTRIBUTION_BOX = (12, 266, 388, 294)
MAX_PANEL_COUNT = 3
MIN_ART_WIDTH = 250
MIN_ART_HEIGHT = 110
MAX_POOR_COLOUR_PIXEL_RATIO = 0.018
WARN_POOR_COLOUR_PIXEL_RATIO = 0.006
MIN_SAFE_COLOUR_PIXEL_RATIO = 0.012
MAX_BLACK_PIXEL_RATIO = 0.22
MIN_BLACK_PIXEL_RATIO = 0.006
MAX_INK_PIXEL_RATIO = 0.45
MAX_SMALL_DETAIL_PIXEL_RATIO = 0.035
SAFE_ART_COLOUR_NAMES = (
    "cream",
    "pale_cream",
    "parchment",
    "pale_yellow",
    "yellow",
    "bright_yellow",
    "gold",
    "dark_gold",
    "red",
    "warm_red",
    "dark_red",
    "blush",
    "peach",
    "rose",
    "orange",
    "burnt_orange",
    "terracotta",
    "brown",
    "dark_brown",
    "maroon",
)

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
REGULAR_FONT_CANDIDATES = (
    FONT_DIR / "BarlowCondensed-Regular.otf",
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)


@dataclass(frozen=True)
class XkcdComic:
    number: int
    title: str
    alt: str
    image_url: str
    comic_url: str
    published: str


@dataclass(frozen=True)
class XkcdSuitability:
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
class XkcdRender:
    comic: XkcdComic
    suitability: XkcdSuitability
    image: Image.Image
    artifact: RenderArtifact


def fetch_xkcd_comic(number: int | None = None, timeout: int = 15) -> XkcdComic:
    url = XKCD_API_CURRENT if number is None else XKCD_API_BY_NUMBER.format(num=int(number))
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return comic_from_json(payload)


def comic_from_json(payload: dict[str, Any]) -> XkcdComic:
    num = int(payload["num"])
    return XkcdComic(
        number=num,
        title=str(payload.get("safe_title") or payload.get("title") or f"xkcd {num}"),
        alt=str(payload.get("alt") or ""),
        image_url=str(payload["img"]),
        comic_url=f"https://xkcd.com/{num}/",
        published="-".join(str(payload.get(part, "")).zfill(2) for part in ("year", "month", "day")).strip("-"),
    )


def download_comic_image(comic: XkcdComic, timeout: int = 20) -> Image.Image:
    with urllib.request.urlopen(comic.image_url, timeout=timeout) as response:
        data = response.read()
    return Image.open(BytesIO(data)).convert("RGBA")


def select_suitable_xkcd(
    latest_number: int,
    attempts: int = 25,
    seed: int | None = None,
    timeout: int = 15,
    exclude_numbers: set[int] | None = None,
) -> tuple[XkcdComic, Image.Image, XkcdSuitability]:
    rng = random.Random(seed)
    excluded = exclude_numbers or set()
    best: tuple[XkcdComic, Image.Image, XkcdSuitability] | None = None
    for _ in range(max(1, attempts)):
        number = rng.randint(1, latest_number)
        if number in excluded:
            continue
        comic = fetch_xkcd_comic(number, timeout=timeout)
        image = download_comic_image(comic, timeout=timeout)
        suitability = analyze_xkcd_image(image)
        if suitability.suitable:
            return comic, image, suitability
        if best is None or suitability.score > best[2].score:
            best = (comic, image, suitability)
    if best is None:
        raise RuntimeError("Could not fetch any xkcd candidates")
    return best


def analyze_xkcd_image(source: Image.Image) -> XkcdSuitability:
    image = _flatten_rgba(source)
    width, height = image.size
    aspect = width / max(1, height)
    fitted = _fit_size(width, height, ART_BOX[2] - ART_BOX[0], ART_BOX[3] - ART_BOX[1])
    panel_count = _estimate_panel_count(image)
    colour_profile = _colour_profile(image)
    black_ratio = _line_density_ratio(image, fitted)
    detail_profile = _detail_profile(image, fitted)

    reasons: list[str] = []
    warnings: list[str] = []
    supported: list[str] = []
    unsupported: list[str] = []
    score = 100

    if aspect < 0.92:
        reasons.append("too tall for a 400x300 landscape card")
        unsupported.append("portrait or tall strip")
        score -= 45
    elif aspect < 1.12:
        warnings.append("near-square comic; accepted only if line art remains readable")
        score -= 8
    else:
        supported.append("landscape or wide layout")

    if fitted[0] < MIN_ART_WIDTH or fitted[1] < MIN_ART_HEIGHT:
        reasons.append(f"art would fit too small at {fitted[0]}x{fitted[1]}")
        unsupported.append("tiny scaled art")
        score -= 40
    else:
        supported.append(f"fits art window at {fitted[0]}x{fitted[1]}")

    if panel_count > MAX_PANEL_COUNT:
        reasons.append(f"estimated {panel_count} panels; maximum is {MAX_PANEL_COUNT}")
        unsupported.append("more than three panels")
        score -= 45
    elif panel_count == 3:
        supported.append("three landscape panels")
    elif panel_count == 2:
        supported.append("two landscape panels")
    else:
        supported.append("single-panel or no panel gutters")

    if colour_profile["poor"] > MAX_POOR_COLOUR_PIXEL_RATIO:
        families = ", ".join(colour_profile["poor_families"]) or "non-panel hues"
        reasons.append(f"poorly reproducible colour: {colour_profile['poor']:.1%} {families} pixels")
        unsupported.append("blue, green, cyan, purple, or magenta-dependent artwork")
        score -= 42
    elif colour_profile["poor"] > WARN_POOR_COLOUR_PIXEL_RATIO:
        families = ", ".join(colour_profile["poor_families"]) or "non-panel hues"
        warnings.append(f"minor poorly reproducible colour present: {colour_profile['poor']:.1%} {families} pixels")
        score -= 8
    if colour_profile["safe"] >= MIN_SAFE_COLOUR_PIXEL_RATIO:
        supported.append(f"panel-safe warm colour present: {colour_profile['safe']:.1%} pixels")
    elif colour_profile["saturated"] > 0.015:
        warnings.append(f"low usable colour after filtering: {colour_profile['saturated']:.1%} saturated pixels")
        score -= 4
    else:
        supported.append("mostly monochrome line art")

    if black_ratio > MAX_BLACK_PIXEL_RATIO:
        reasons.append(f"too dense after 400x300 conversion: {black_ratio:.1%} black pixels")
        unsupported.append("dense diagram, table, or text-heavy comic")
        score -= 35
    elif black_ratio < MIN_BLACK_PIXEL_RATIO:
        reasons.append(f"too little surviving line art after scaling: {black_ratio:.1%} black pixels")
        unsupported.append("line art too faint after scaling")
        score -= 30
    else:
        supported.append("line art survives monochrome conversion")

    if detail_profile["ink"] > MAX_INK_PIXEL_RATIO:
        reasons.append(f"too much total ink/detail for the small display: {detail_profile['ink']:.1%} non-white pixels")
        unsupported.append("busy annotation, table, map, or dense chart")
        score -= 35
    elif detail_profile["small"] > MAX_SMALL_DETAIL_PIXEL_RATIO:
        reasons.append(f"too much tiny detail for the small display: {detail_profile['small']:.1%} fine-detail pixels")
        unsupported.append("tiny annotations or fine chart marks")
        score -= 35
    else:
        supported.append("detail level is readable at frame size")

    if width > height * 3.2:
        warnings.append("very wide comic; may lose small labels")
        score -= 12

    score = max(0, min(100, score))
    return XkcdSuitability(
        suitable=not reasons,
        score=score,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
        panel_count=panel_count,
        aspect_ratio=round(aspect, 3),
        saturated_pixel_ratio=round(colour_profile["saturated"], 4),
        safe_colour_pixel_ratio=round(colour_profile["safe"], 4),
        poor_colour_pixel_ratio=round(colour_profile["poor"], 4),
        dominant_poor_colour_families=tuple(colour_profile["poor_families"]),
        black_pixel_ratio=round(black_ratio, 4),
        ink_pixel_ratio=round(detail_profile["ink"], 4),
        small_detail_pixel_ratio=round(detail_profile["small"], 4),
        fitted_art_size=fitted,
        supported_features=tuple(supported),
        unsupported_features=tuple(unsupported),
    )


def render_xkcd_card(comic: XkcdComic, source: Image.Image, suitability: XkcdSuitability | None = None) -> XkcdRender:
    suitability = suitability or analyze_xkcd_image(source)
    base = Image.new("RGB", (WIDTH, HEIGHT), TEMPLATE_COLOURS["white"].rgb)
    draw = ImageDraw.Draw(base)

    title = f"xkcd #{comic.number}: {comic.title}"
    _draw_fitted_text(draw, TITLE_BOX, title, TEMPLATE_COLOURS["black"].rgb, start_size=24, min_size=13)

    art_size = _fit_size(source.width, source.height, ART_BOX[2] - ART_BOX[0], ART_BOX[3] - ART_BOX[1])
    art = _prepare_display_art(_flatten_rgba(source), art_size)
    art_x = ART_BOX[0] + ((ART_BOX[2] - ART_BOX[0]) - art.width) // 2
    art_y = ART_BOX[1] + ((ART_BOX[3] - ART_BOX[1]) - art.height) // 2
    base.paste(art, (art_x, art_y))

    attribution = f"xkcd / Randall Munroe | {XKCD_LICENSE}"
    _draw_fitted_text(draw, ATTRIBUTION_BOX, attribution, TEMPLATE_COLOURS["red"].rgb, start_size=18, min_size=11)

    artifact = render_to_artifact(base, f"xkcd_{comic.number}", [comic.comic_url])
    artifact.metadata.update(
        {
            "provider_id": "xkcd_experimental",
            "provider_name": "xkcd Comic Experimental",
            "xkcd_number": comic.number,
            "xkcd_title": comic.title,
            "xkcd_alt_text": comic.alt,
            "source": XKCD_SOURCE_NAME,
            "source_name": XKCD_ATTRIBUTION,
            "source_url": comic.comic_url,
            "image_url": comic.image_url,
            "attribution": attribution,
            "attribution_url": "https://xkcd.com/license.html",
            "license": XKCD_LICENSE,
            "license_url": XKCD_LICENSE_URL,
            "data_transformations": (
                "Rendered as Ditherloom 400x300 panel-aware cartoon art. "
                "Warm xkcd colour is allowed only when it fits red/yellow/orange/brown Ditherloom-safe recipes. "
                "Blue, green, cyan, purple, and magenta-heavy artwork is rejected as poorly reproducible. "
                "Accepted colour art is pretreated with 30% colour boost and 15% contrast boost before hybrid/photo conversion. "
                "Exact black, white, yellow, and red panel colours receive no dithering. "
                "No generic near-colour snapping is used."
            ),
            "suitability": {
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
            },
        }
    )
    return XkcdRender(comic=comic, suitability=suitability, image=base, artifact=artifact)


def write_xkcd_render(render: XkcdRender, output_dir: Path) -> dict[str, Path]:
    stem = f"xkcd_{render.comic.number:04d}_{_slug(render.comic.title)}"
    paths = write_artifact(render.artifact, output_dir, stem)
    original_path = output_dir / f"{stem}.source.png"
    render.image.save(original_path)
    paths["source_card"] = original_path
    return paths


def _flatten_rgba(source: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    background.alpha_composite(rgba)
    return background.convert("RGB")


def _fit_size(width: int, height: int, max_width: int, max_height: int) -> tuple[int, int]:
    scale = min(max_width / max(1, width), max_height / max(1, height), 1.0)
    return max(1, int(round(width * scale))), max(1, int(round(height * scale)))


def _prepare_display_art(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    colour_profile = _colour_profile(image)
    if colour_profile["safe"] >= MIN_SAFE_COLOUR_PIXEL_RATIO and colour_profile["poor"] <= MAX_POOR_COLOUR_PIXEL_RATIO:
        return _prepare_colour_art(image, size)
    return _prepare_line_art(image, size)


def _prepare_line_art(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    grayscale = ImageOps.grayscale(image)
    grayscale = ImageOps.autocontrast(grayscale, cutoff=1)
    resized = grayscale.resize(size, Image.Resampling.LANCZOS)
    threshold = _otsu_threshold(resized)
    threshold = max(96, min(210, threshold + 10))
    output = Image.new("RGB", resized.size, TEMPLATE_COLOURS["white"].rgb)
    pixels = resized.load()
    out = output.load()
    for y in range(resized.height):
        for x in range(resized.width):
            if pixels[x, y] < threshold:
                out[x, y] = TEMPLATE_COLOURS["black"].rgb
                continue
            out[x, y] = TEMPLATE_COLOURS["white"].rgb
    return output


def _prepare_colour_art(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    resized = image.resize(size, Image.Resampling.LANCZOS).convert("RGB")
    resized = ImageEnhance.Color(resized).enhance(1.30)
    resized = ImageEnhance.Contrast(resized).enhance(1.15)
    output = Image.new("RGB", resized.size, TEMPLATE_COLOURS["white"].rgb)
    pixels = resized.load()
    out = output.load()
    for y in range(resized.height):
        for x in range(resized.width):
            rgb = pixels[x, y]
            if _is_neutral(rgb) or _safe_art_colour(rgb) is not None:
                out[x, y] = _normalise_panel_extremes(rgb)
                continue
            grey = int(round(rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114))
            out[x, y] = (grey, grey, grey) if grey < 210 else TEMPLATE_COLOURS["white"].rgb
    return output


def _normalise_panel_extremes(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = rgb
    high = max(rgb)
    low = min(rgb)
    if high <= 70:
        return TEMPLATE_COLOURS["black"].rgb
    if low >= 224 and high - low <= 50:
        return TEMPLATE_COLOURS["white"].rgb
    if r >= 200 and g <= 76 and b <= 76:
        return TEMPLATE_COLOURS["red"].rgb
    if r >= 200 and g >= 176 and b <= 84 and abs(r - g) <= 82:
        return TEMPLATE_COLOURS["bright_yellow"].rgb
    return rgb


def _safe_art_colour(rgb: tuple[int, int, int]) -> str | None:
    if _is_neutral(rgb):
        return None
    family = _colour_family(rgb)
    if family == "yellow":
        return "bright_yellow" if max(rgb) > 210 else "yellow"
    if family == "orange":
        return "orange"
    if family == "red":
        return "red" if max(rgb) > 170 else "dark_red"
    if family == "pink":
        return "rose"
    if family == "brown":
        return "brown"
    if family == "cream":
        return "parchment"
    return None


def _recipe_pixel_rgb(colour_name: str, x: int, y: int) -> tuple[int, int, int]:
    colour = TEMPLATE_COLOURS[colour_name]
    if colour.recipe is None:
        if colour.name == "red":
            return PACKET_RGB[3]
        if colour.name in {"yellow", "bright_yellow"}:
            return PACKET_RGB[2]
        if colour.name == "white":
            return PACKET_RGB[1]
        return PACKET_RGB[0]
    return PACKET_RGB[ordered_code(colour.recipe, x, y)]


def _line_density_ratio(image: Image.Image, size: tuple[int, int]) -> float:
    grayscale = ImageOps.grayscale(image)
    grayscale = ImageOps.autocontrast(grayscale, cutoff=1)
    resized = grayscale.resize(size, Image.Resampling.LANCZOS)
    colour_resized = image.resize(size, Image.Resampling.LANCZOS).convert("RGB")
    threshold = max(96, min(210, _otsu_threshold(resized) + 10))
    pixels = resized.load()
    colour_pixels = colour_resized.load()
    black = 0
    total = max(1, resized.width * resized.height)
    for y in range(resized.height):
        for x in range(resized.width):
            rgb = colour_pixels[x, y]
            if _safe_art_colour(rgb) is not None and pixels[x, y] >= 58:
                continue
            if pixels[x, y] < threshold:
                black += 1
    return black / total


def _detail_profile(image: Image.Image, size: tuple[int, int]) -> dict[str, float]:
    art = _prepare_display_art(image, size).convert("RGB")
    pixels = art.load()
    white = TEMPLATE_COLOURS["white"].rgb
    width, height = art.size
    ink = 0
    small_detail = 0
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == white:
                continue
            ink += 1
            neighbours = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    xx = x + dx
                    yy = y + dy
                    if 0 <= xx < width and 0 <= yy < height and pixels[xx, yy] != white:
                        neighbours += 1
            if neighbours <= 3:
                small_detail += 1
    total = max(1, width * height)
    return {"ink": ink / total, "small": small_detail / total}


def _otsu_threshold(image: Image.Image) -> int:
    histogram = image.histogram()
    total = sum(histogram)
    if total <= 0:
        return 180
    sum_total = sum(i * count for i, count in enumerate(histogram))
    weight_background = 0
    sum_background = 0
    best_variance = -1.0
    best_threshold = 180
    for threshold, count in enumerate(histogram):
        weight_background += count
        if weight_background == 0:
            continue
        weight_foreground = total - weight_background
        if weight_foreground == 0:
            break
        sum_background += threshold * count
        mean_background = sum_background / weight_background
        mean_foreground = (sum_total - sum_background) / weight_foreground
        variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = threshold
    return best_threshold


def _colour_profile(image: Image.Image) -> dict[str, Any]:
    sample = image.resize((min(220, image.width), max(1, round(image.height * min(220, image.width) / image.width))), Image.Resampling.BILINEAR)
    pixels = list(sample.getdata())
    if not pixels:
        return {"saturated": 0.0, "safe": 0.0, "poor": 0.0, "poor_families": ()}
    saturated = 0
    safe = 0
    poor = 0
    poor_families: dict[str, int] = {}
    for r, g, b in pixels:
        rgb = (r, g, b)
        if _is_neutral(rgb):
            continue
        saturated += 1
        family = _colour_family(rgb)
        if family in {"red", "yellow", "orange", "brown", "pink", "cream"}:
            safe += 1
        else:
            poor += 1
            poor_families[family] = poor_families.get(family, 0) + 1
    dominant = tuple(
        family
        for family, _ in sorted(poor_families.items(), key=lambda item: item[1], reverse=True)[:3]
    )
    total = len(pixels)
    return {
        "saturated": saturated / total,
        "safe": safe / total,
        "poor": poor / total,
        "poor_families": dominant,
    }


def _is_neutral(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    high = max(r, g, b)
    low = min(r, g, b)
    return high < 86 or high - low <= 44


def _colour_family(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    h, s, v = rgb_to_hsv(r / 255, g / 255, b / 255)
    hue = h * 360
    if s < 0.18 or v < 0.20:
        return "neutral"
    if r >= 190 and g >= 150 and b >= 115 and b <= g + 35:
        return "cream"
    if 345 <= hue or hue < 18:
        return "red"
    if 18 <= hue < 43:
        return "orange" if v > 0.45 else "brown"
    if 43 <= hue < 72:
        return "yellow"
    if 320 <= hue < 345 and r >= 170 and b <= max(130, g + 45):
        return "pink"
    if 72 <= hue < 170:
        return "green"
    if 170 <= hue < 205:
        return "cyan"
    if 205 <= hue < 265:
        return "blue"
    if 265 <= hue < 320:
        return "purple"
    return "magenta"


def _black_pixel_ratio(image: Image.Image) -> float:
    pixels = list(image.convert("RGB").getdata())
    if not pixels:
        return 0.0
    black = sum(1 for pixel in pixels if pixel == TEMPLATE_COLOURS["black"].rgb)
    return black / len(pixels)


def _estimate_panel_count(image: Image.Image) -> int:
    grayscale = ImageOps.grayscale(image.resize((min(640, image.width), max(1, round(image.height * min(640, image.width) / image.width))), Image.Resampling.BILINEAR))
    threshold = _otsu_threshold(grayscale)
    width, height = grayscale.size
    pixels = grayscale.load()
    column_black_counts = []
    for x in range(width):
        column_black_counts.append(sum(1 for y in range(height) if pixels[x, y] < threshold - 8))
    whitespace_runs: list[tuple[int, int]] = []
    run_start: int | None = None
    for x, count in enumerate(column_black_counts):
        density = count / max(1, height)
        if density < 0.006:
            if run_start is None:
                run_start = x
        elif run_start is not None:
            whitespace_runs.append((run_start, x - 1))
            run_start = None
    if run_start is not None:
        whitespace_runs.append((run_start, width - 1))

    min_run = max(8, int(width * 0.025))
    gutters = [
        (start, end)
        for start, end in whitespace_runs
        if end - start + 1 >= min_run and width * 0.08 < (start + end) / 2 < width * 0.92
    ]
    panel_count = 1 + len(gutters)
    return max(1, min(8, panel_count))


def _draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fill: tuple[int, int, int],
    start_size: int,
    min_size: int,
) -> None:
    x1, y1, x2, y2 = box
    value = str(text).strip()
    font = _fit_regular_font(value, x2 - x1, y2 - y1, start_size, min_size)
    left, top, right, bottom = font.getbbox(value)
    x = x1 + (x2 - x1 - (right - left)) / 2 - left
    y = y1 + (y2 - y1 - (bottom - top)) / 2 - top
    draw.text((int(x), int(y)), value, font=font, fill=fill)


def _fit_regular_font(text: str, max_width: int, max_height: int, start_size: int, min_size: int) -> ImageFont.ImageFont:
    for size in range(start_size, min_size - 1, -1):
        font = _load_regular_font(size)
        left, top, right, bottom = font.getbbox(text)
        if right - left <= max_width and bottom - top <= max_height:
            return font
    return _load_regular_font(min_size)


def _load_regular_font(size: int) -> ImageFont.ImageFont:
    for path in REGULAR_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    raise RuntimeError("Barlow Condensed regular font is required for xkcd attribution rendering.")


def _slug(value: str) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in clean:
        clean = clean.replace("__", "_")
    return clean.strip("_")[:42] or "comic"
