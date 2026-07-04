from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance
import segno

from .comics_selector import ComicCandidate, select_best_comic_candidate
from .renderer.pack import RenderArtifact, render_to_artifact, write_artifact
from .renderer.palette import PACKET_RGB, PREVIEW_RGB, TEMPLATE_COLOURS
from .xkcd_provider import (
    HEIGHT,
    WIDTH,
    _flatten_rgba,
    _fit_size,
    _fit_regular_font,
    analyze_xkcd_image,
)

LEFT_ART_BOX = (4, 4, 300, 296)
RIGHT_ATTRIBUTION_LINE_X = 309
RIGHT_ATTRIBUTION_BOXES = (
    (316, 14, 396, 44),
    (316, 48, 396, 78),
    (316, 82, 396, 112),
    (316, 116, 396, 142),
)
RIGHT_QR_BOX = (316, 150, 396, 230)
RIGHT_HOST_BOX = (316, 240, 396, 292)


@dataclass(frozen=True)
class WebcomicSource:
    source_id: str
    provider_id: str
    provider_name: str
    feed_url: str
    home_url: str
    attribution: str
    attribution_url: str
    license_name: str
    license_url: str
    image_host_allowlist: tuple[str, ...] = ()
    candidate_limit: int = 12
    allow_pastel_backgrounds: bool = False
    allow_display_pixel_art: bool = False
    allow_hybrid_illustration: bool = False
    preserve_full_layout: bool = False
    reflow_vertical_strip: bool = False
    vertical_panel_count: int = 0
    panel_grid_layout: tuple[int, ...] = ()


@dataclass(frozen=True)
class WebcomicRender:
    source: WebcomicSource
    selection: Any
    image: Image.Image
    artifact: RenderArtifact


WEBCOMIC_SOURCES: dict[str, WebcomicSource] = {
    "diesel_sweeties": WebcomicSource(
        source_id="diesel_sweeties",
        provider_id="diesel_sweeties",
        provider_name="Diesel Sweeties",
        feed_url="https://www.dieselsweeties.com/ds-unifeed.xml",
        home_url="https://www.dieselsweeties.com/",
        attribution="Diesel Sweeties / R. Stevens | CC BY-NC",
        attribution_url="https://www.dieselsweeties.com/",
        license_name="CC BY-NC",
        license_url="https://creativecommons.org/licenses/by-nc/2.5/",
        image_host_allowlist=("dieselsweeties.com", "www.dieselsweeties.com"),
        allow_display_pixel_art=True,
        preserve_full_layout=True,
    ),
    "mimi_eunice": WebcomicSource(
        source_id="mimi_eunice",
        provider_id="mimi_eunice",
        provider_name="Mimi & Eunice",
        feed_url="https://mimiandeunice.com/feed/",
        home_url="https://mimiandeunice.com/",
        attribution="Mimi & Eunice / Nina Paley | CC BY-SA",
        attribution_url="https://mimiandeunice.com/about/",
        license_name="CC BY-SA",
        license_url="https://creativecommons.org/licenses/by-sa/3.0/",
        image_host_allowlist=("mimiandeunice.com", "www.mimiandeunice.com"),
        candidate_limit=40,
        allow_pastel_backgrounds=True,
        reflow_vertical_strip=True,
        vertical_panel_count=3,
        panel_grid_layout=(2, 1),
    ),
}


def render_webcomic_provider(provider_id: str, output_dir: Path, stem: str) -> tuple[RenderArtifact, WebcomicSource, Any]:
    source = WEBCOMIC_SOURCES[provider_id]
    candidates = expand_webcomic_candidates(source, fetch_webcomic_candidates(source, limit=source.candidate_limit))
    selection = select_best_comic_candidate(candidates, analyzer=_source_analyzer(source))
    if not selection.suitability.suitable:
        reasons = "; ".join(selection.suitability.reasons) or "no suitable display candidate"
        raise RuntimeError(f"{source.provider_name} has no suitable current comic for Ditherloom display: {reasons}")
    render = render_webcomic_card(source, selection)
    paths = write_artifact(render.artifact, output_dir, stem)
    render.image.save(output_dir / f"{stem}.source.png")
    return render.artifact, source, selection


def fetch_webcomic_candidates(source: WebcomicSource, *, timeout: int = 18, limit: int = 12) -> list[ComicCandidate]:
    request = urllib.request.Request(source.feed_url, headers={"User-Agent": "Ditherloom-HA-Comics/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    root = ET.fromstring(payload)
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    candidates: list[ComicCandidate] = []
    for item in items[: max(1, limit)]:
        title = _text(item, "title") or source.provider_name
        link = _text(item, "link") or _atom_link(item) or source.home_url
        body = " ".join(
            value
            for value in (
                _text(item, "description"),
                _text(item, "encoded"),
                _namespaced_text(item, "http://purl.org/rss/1.0/modules/content/", "encoded"),
                _namespaced_text(item, "http://www.w3.org/2005/Atom", "content"),
                _namespaced_text(item, "http://search.yahoo.com/mrss/", "description"),
            )
            if value
        )
        image_urls = _media_urls(item) + _image_urls_from_html(body)
        for image_url in image_urls:
            absolute = urllib.parse.urljoin(link, html.unescape(image_url))
            if not _allowed_image_url(absolute, source):
                continue
            try:
                image = _download_image(absolute, timeout=timeout)
            except Exception:
                continue
            candidates.append(
                ComicCandidate(
                    source_id=source.source_id,
                    source_name=source.provider_name,
                    title=html.unescape(title).strip() or source.provider_name,
                    source_url=link,
                    image_url=absolute,
                    image=image,
                )
            )
            break
    if not candidates:
        raise RuntimeError(f"No usable image candidates found in {source.provider_name} feed")
    return candidates


def expand_webcomic_candidates(source: WebcomicSource, candidates: list[ComicCandidate]) -> list[ComicCandidate]:
    expanded: list[ComicCandidate] = []
    for candidate in candidates:
        if source.reflow_vertical_strip:
            expanded.append(_reflow_vertical_strip_candidate(source, candidate))
        else:
            expanded.append(_whole_layout_candidate(source, candidate))
    return expanded


def render_webcomic_card(source: WebcomicSource, selection: Any) -> WebcomicRender:
    candidate = selection.candidate
    base = Image.new("RGB", (WIDTH, HEIGHT), TEMPLATE_COLOURS["white"].rgb)
    draw = ImageDraw.Draw(base)

    art_size = _fit_size(
        candidate.image.width,
        candidate.image.height,
        LEFT_ART_BOX[2] - LEFT_ART_BOX[0],
        LEFT_ART_BOX[3] - LEFT_ART_BOX[1],
    )
    art = _prepare_packet_colour_art(_flatten_rgba(candidate.image), art_size)
    art_x = LEFT_ART_BOX[0] + ((LEFT_ART_BOX[2] - LEFT_ART_BOX[0]) - art.width) // 2
    if candidate.metadata.get("left_justify_art"):
        art_x = LEFT_ART_BOX[0]
    art_y = LEFT_ART_BOX[1] + ((LEFT_ART_BOX[3] - LEFT_ART_BOX[1]) - art.height) // 2
    base.paste(art, (art_x, art_y))
    _draw_right_attribution(base, draw, source, candidate.source_url)

    artifact = render_to_artifact(base, f"{source.source_id}_{_slug(candidate.title)}", [candidate.source_url])
    artifact.metadata.update(
        {
            "provider_id": source.provider_id,
            "provider_name": source.provider_name,
            "source": source.source_id,
            "source_name": source.provider_name,
            "source_url": candidate.source_url,
            "image_url": candidate.image_url,
            "attribution": source.attribution,
            "attribution_url": source.attribution_url,
            "license": source.license_name,
            "license_url": source.license_url,
            "comic_title": candidate.title,
            "comic_suitability": {
                "suitable": selection.suitability.suitable,
                "score": selection.suitability.score,
                "reasons": list(selection.suitability.reasons),
                "warnings": list(selection.suitability.warnings),
                "panel_count": selection.suitability.panel_count,
                "aspect_ratio": selection.suitability.aspect_ratio,
                "poor_colour_pixel_ratio": selection.suitability.poor_colour_pixel_ratio,
                "fitted_art_size": list(selection.suitability.fitted_art_size),
            },
            "qr_url": candidate.source_url,
            "data_transformations": (
                "Rendered through the Ditherloom Comics 400x300 selector and hybrid comic renderer. "
                "Non-xkcd webcomics preserve all panels where possible; very wide strips are reflowed into "
                "the left comic area rather than clipped to one panel. Accepted colour art uses 30% colour "
                "boost and 15% contrast boost. Exact black, white, yellow, and red panel colours receive no "
                "dithering, near-white comic backgrounds are protected as clean panel white, and source "
                "attribution is rendered separately in undithered red with a direct source QR code."
            ),
        }
    )
    return WebcomicRender(source=source, selection=selection, image=base, artifact=artifact)


def render_webcomic_sample_card(source: WebcomicSource, selection: Any) -> Image.Image:
    candidate = selection.candidate
    base = Image.new("RGB", (WIDTH, HEIGHT), TEMPLATE_COLOURS["white"].rgb)
    draw = ImageDraw.Draw(base)

    art_size = _fit_size(
        candidate.image.width,
        candidate.image.height,
        LEFT_ART_BOX[2] - LEFT_ART_BOX[0],
        LEFT_ART_BOX[3] - LEFT_ART_BOX[1],
    )
    art = _prepare_sample_colour_art(_flatten_rgba(candidate.image), art_size)
    art_x = LEFT_ART_BOX[0] + ((LEFT_ART_BOX[2] - LEFT_ART_BOX[0]) - art.width) // 2
    if candidate.metadata.get("left_justify_art"):
        art_x = LEFT_ART_BOX[0]
    art_y = LEFT_ART_BOX[1] + ((LEFT_ART_BOX[3] - LEFT_ART_BOX[1]) - art.height) // 2
    base.paste(art, (art_x, art_y))
    _draw_right_attribution(base, draw, source, candidate.source_url)
    return base


def _prepare_sample_colour_art(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    resized = image.resize(size, Image.Resampling.LANCZOS).convert("RGB")
    resized = ImageEnhance.Color(resized).enhance(1.30)
    resized = ImageEnhance.Contrast(resized).enhance(1.15)
    return _atkinson_dither_to_display_palette(resized, PREVIEW_RGB, PREVIEW_RGB[1])


def _prepare_packet_colour_art(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    resized = image.resize(size, Image.Resampling.LANCZOS).convert("RGB")
    resized = ImageEnhance.Color(resized).enhance(1.30)
    resized = ImageEnhance.Contrast(resized).enhance(1.15)
    return _atkinson_dither_to_display_palette(resized, PACKET_RGB, TEMPLATE_COLOURS["white"].rgb)


def _atkinson_dither_to_display_preview(image: Image.Image) -> Image.Image:
    return _atkinson_dither_to_display_palette(image, PREVIEW_RGB, PREVIEW_RGB[1])


def _atkinson_dither_to_display_palette(
    image: Image.Image,
    palette: dict[int, tuple[int, int, int]],
    protected_white_rgb: tuple[int, int, int],
) -> Image.Image:
    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    protected_white = [
        [_is_protected_comic_white(rgb_image.getpixel((x, y))) for x in range(width)]
        for y in range(height)
    ]
    pixels = [
        [[float(channel) for channel in rgb_image.getpixel((x, y))] for x in range(width)]
        for y in range(height)
    ]
    output = Image.new("RGB", (width, height))
    out = output.load()
    for y in range(height):
        for x in range(width):
            if protected_white[y][x]:
                out[x, y] = protected_white_rgb
                continue
            r, g, b = pixels[y][x]
            code, nr, ng, nb = _closest_palette_code_and_rgb(palette, r, g, b)
            out[x, y] = palette[code]
            _diffuse_atkinson_preview_error(
                pixels,
                protected_white,
                x,
                y,
                width,
                height,
                (r - nr, g - ng, b - nb),
            )
    return output


def _closest_palette_code_and_rgb(
    palette: dict[int, tuple[int, int, int]],
    r: float,
    g: float,
    b: float,
) -> tuple[int, int, int, int]:
    best_code = 0
    best_rgb = palette[0]
    best_distance = float("inf")
    for code, (pr, pg, pb) in palette.items():
        distance = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if distance < best_distance:
            best_distance = distance
            best_code = code
            best_rgb = (pr, pg, pb)
    return best_code, best_rgb[0], best_rgb[1], best_rgb[2]


def _diffuse_atkinson_preview_error(
    pixels: list[list[list[float]]],
    protected_white: list[list[bool]],
    x: int,
    y: int,
    width: int,
    height: int,
    error: tuple[float, float, float],
) -> None:
    for dx, dy, weight in (
        (1, 0, 1 / 8),
        (2, 0, 1 / 8),
        (-1, 1, 1 / 8),
        (0, 1, 1 / 8),
        (1, 1, 1 / 8),
        (0, 2, 1 / 8),
    ):
        nx = x + dx
        ny = y + dy
        if 0 <= nx < width and 0 <= ny < height and not protected_white[ny][nx]:
            target = pixels[ny][nx]
            target[0] = max(0.0, min(255.0, target[0] + error[0] * weight))
            target[1] = max(0.0, min(255.0, target[1] + error[1] * weight))
            target[2] = max(0.0, min(255.0, target[2] + error[2] * weight))


def _is_protected_comic_white(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return r >= 215 and g >= 210 and b >= 195 and max(rgb) - min(rgb) <= 55


def _draw_right_attribution(base: Image.Image, draw: ImageDraw.ImageDraw, source: WebcomicSource, source_url: str) -> None:
    red = TEMPLATE_COLOURS["red"].rgb
    draw.line((RIGHT_ATTRIBUTION_LINE_X, 8, RIGHT_ATTRIBUTION_LINE_X, 292), fill=red, width=1)
    for box, text, start_size in zip(
        RIGHT_ATTRIBUTION_BOXES,
        _right_attribution_header_lines(source),
        (16, 16, 16, 13),
        strict=True,
    ):
        _draw_left_fitted_text(draw, box, text, red, start_size, 8)
    base.paste(_source_qr_image(source_url, RIGHT_QR_BOX), RIGHT_QR_BOX[:2])
    _draw_left_fitted_text(draw, RIGHT_HOST_BOX, _source_host_label(source, source_url), red, 13, 8)


def _right_attribution_header_lines(source: WebcomicSource) -> tuple[str, str, str, str]:
    creator = source.attribution.split(" / ", 1)[1].split(" | ", 1)[0] if " / " in source.attribution else source.attribution
    return (source.provider_name, creator, source.license_name, "Scan source")


def _source_host_label(source: WebcomicSource, source_url: str) -> str:
    host = urllib.parse.urlparse(source_url).hostname or urllib.parse.urlparse(source.home_url).hostname or source.home_url
    if host.startswith("www."):
        host = host[4:]
    return host


def _source_qr_image(source_url: str, box: tuple[int, int, int, int]) -> Image.Image:
    max_width = box[2] - box[0]
    max_height = box[3] - box[1]
    qr = segno.make(source_url, error="m")
    quiet_zone = 3
    symbol_width, symbol_height = qr.symbol_size(scale=1, border=0)
    scale = max(1, min((max_width - quiet_zone * 2) // symbol_width, (max_height - quiet_zone * 2) // symbol_height))
    png = BytesIO()
    qr.save(png, kind="png", scale=scale, border=0, dark="black", light="white")
    png.seek(0)
    rendered = Image.open(png).convert("RGB")
    canvas = Image.new("RGB", (max_width, max_height), TEMPLATE_COLOURS["white"].rgb)
    x = quiet_zone
    y = (max_height - rendered.height) // 2
    canvas.paste(rendered, (x, y))
    return canvas


def _draw_left_fitted_text(
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
    left, top, _right, bottom = font.getbbox(value)
    y = y1 + (y2 - y1 - (bottom - top)) / 2 - top
    draw.text((x1 - left, int(y)), value, font=font, fill=fill)


def _source_analyzer(source: WebcomicSource):
    def analyzer(image: Image.Image):
        suitability = analyze_xkcd_image(image)
        if suitability.suitable:
            return suitability
        if _source_policy_accepts(source, suitability):
            return replace(
                suitability,
                suitable=True,
                score=max(suitability.score, 61),
                warnings=tuple(suitability.warnings)
                + (f"{source.provider_name} accepted by source policy after shared display analysis",),
            )
        return suitability

    return analyzer


def _source_policy_accepts(source: WebcomicSource, suitability: Any) -> bool:
    fit_width, fit_height = suitability.fitted_art_size
    if source.preserve_full_layout or source.reflow_vertical_strip:
        if fit_width >= 120 and fit_height >= 80 and suitability.ink_pixel_ratio <= 0.82:
            return True
    if fit_width < 150 or fit_height < 130 or suitability.panel_count > 3:
        return False
    if source.allow_pastel_backgrounds:
        if (
            suitability.poor_colour_pixel_ratio <= 0.30
            and suitability.black_pixel_ratio <= 0.48
            and suitability.small_detail_pixel_ratio <= 0.05
        ):
            return True
    if source.allow_display_pixel_art:
        if suitability.poor_colour_pixel_ratio <= 0.24 and suitability.black_pixel_ratio <= 0.40:
            return True
    if source.allow_hybrid_illustration:
        if suitability.poor_colour_pixel_ratio <= 0.50 and suitability.ink_pixel_ratio <= 0.75:
            return True
    return False


def _whole_layout_candidate(source: WebcomicSource, candidate: ComicCandidate) -> ComicCandidate:
    image = _trim_protected_white(_flatten_rgba(candidate.image))
    return replace(
        candidate,
        source_id=source.source_id,
        source_name=source.provider_name,
        title=candidate.title,
        image=image,
        metadata={**candidate.metadata, "layout": "whole", "left_justify_art": True},
    )


def _reflow_vertical_strip_candidate(source: WebcomicSource, candidate: ComicCandidate) -> ComicCandidate:
    image = _trim_protected_white(_flatten_rgba(candidate.image))
    width, height = image.size
    panel_count = source.vertical_panel_count
    if panel_count < 2:
        panel_count = 4 if width / max(1, height) > 2.7 else 3
    panels: list[Image.Image] = []
    for index in range(panel_count):
        left = int(width * index / panel_count)
        right = int(width * (index + 1) / panel_count)
        panel = image.crop((left, 0, right, height))
        panels.append(_trim_protected_white(panel))
    grid = _compose_panel_grid(panels, source.panel_grid_layout or (panel_count,))
    return replace(
        candidate,
        source_id=source.source_id,
        source_name=source.provider_name,
        title=f"{candidate.title} (all panels)",
        image=grid,
        metadata={**candidate.metadata, "layout": "all_panels_reflow", "left_justify_art": True},
    )


def _compose_panel_grid(panels: list[Image.Image], layout: tuple[int, ...]) -> Image.Image:
    area_width = LEFT_ART_BOX[2] - LEFT_ART_BOX[0]
    area_height = LEFT_ART_BOX[3] - LEFT_ART_BOX[1]
    gutter = 4
    columns = max(layout) if layout else len(panels)
    rows = len(layout) if layout else 1
    cell_width = max(1, (area_width - gutter * (columns - 1)) // columns)
    cell_height = max(1, (area_height - gutter * (rows - 1)) // rows)
    canvas = Image.new("RGB", (area_width, area_height), TEMPLATE_COLOURS["white"].rgb)
    index = 0
    y = 0
    for row_columns in layout:
        row_width = cell_width * row_columns + gutter * (row_columns - 1)
        x = (area_width - row_width) // 2
        for _ in range(row_columns):
            if index >= len(panels):
                break
            panel = panels[index]
            size = _fit_size(panel.width, panel.height, cell_width, cell_height)
            art = panel.resize(size, Image.Resampling.LANCZOS).convert("RGB")
            canvas.paste(art, (x + (cell_width - size[0]) // 2, y + (cell_height - size[1]) // 2))
            x += cell_width + gutter
            index += 1
        y += cell_height + gutter
    return canvas


def _trim_protected_white(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        for x in range(width):
            if not _is_protected_comic_white(pixels[x, y]):
                xs.append(x)
                ys.append(y)
    if not xs:
        return rgb
    pad = 4
    return rgb.crop(
        (
            max(0, min(xs) - pad),
            max(0, min(ys) - pad),
            min(width, max(xs) + pad + 1),
            min(height, max(ys) + pad + 1),
        )
    )


def _text(item: ET.Element, tag: str) -> str:
    found = item.find(tag)
    return (found.text or "").strip() if found is not None else ""


def _namespaced_text(item: ET.Element, namespace: str, tag: str) -> str:
    found = item.find(f"{{{namespace}}}{tag}")
    return (found.text or "").strip() if found is not None else ""


def _atom_link(item: ET.Element) -> str:
    found = item.find("{http://www.w3.org/2005/Atom}link")
    if found is None:
        return ""
    return str(found.attrib.get("href") or "")


def _media_urls(item: ET.Element) -> list[str]:
    urls: list[str] = []
    for element in item.iter():
        tag = element.tag.rsplit("}", 1)[-1].lower()
        if tag in {"content", "thumbnail"} and element.attrib.get("url"):
            urls.append(str(element.attrib["url"]))
        if tag == "enclosure" and str(element.attrib.get("type", "")).startswith("image/") and element.attrib.get("url"):
            urls.append(str(element.attrib["url"]))
    return urls


def _image_urls_from_html(value: str) -> list[str]:
    return re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", html.unescape(value), flags=re.IGNORECASE)


def _allowed_image_url(url: str, source: WebcomicSource) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if source.image_host_allowlist and parsed.hostname not in source.image_host_allowlist:
        return False
    return True


def _download_image(url: str, timeout: int) -> Image.Image:
    request = urllib.request.Request(url, headers={"User-Agent": "Ditherloom-HA-Comics/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    image = Image.open(BytesIO(data))
    if getattr(image, "is_animated", False):
        image.seek(0)
    return image.convert("RGBA")


def _slug(value: str) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in clean:
        clean = clean.replace("__", "_")
    return clean.strip("_")[:42] or "comic"
