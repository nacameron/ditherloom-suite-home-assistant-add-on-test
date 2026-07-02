from __future__ import annotations

import json
import sys
import types
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)
ditherloom_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon")
ditherloom_package.__path__ = [str(ROOT / "custom_components" / "ditherloom_suite_ha_addon")]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon", ditherloom_package)

from custom_components.ditherloom_suite_ha_addon.xkcd_provider import (  # noqa: E402
    XkcdComic,
    analyze_xkcd_image,
    download_comic_image,
    fetch_xkcd_comic,
    render_xkcd_card,
    write_xkcd_render,
)

SAMPLE_IDS = (
    353,   # Python
    927,   # Standards
    1597,  # Git
    303,   # Compiling
    1492,  # Dress Color, colour-dependent
    1811,  # Best-Tasting Colors, colour-dependent
    2333,  # COVID Risk Chart, colour-coded
    2734,  # Electron Color, coloured diagrams
    1470,  # Kix, red annotation
    1725,  # Linear Regression, red annotation
    1902,  # State Borders, red annotation
    2258,  # Solar System Changes, red/yellow annotation
    2351,  # Standard Model Changes, red/yellow annotation
    2639,  # Periodic Table Changes, strong red/yellow annotation
    2794,  # Alphabet Notes, strong red/yellow annotation
    3012,  # The Future of Orion, green-heavy rejection
    1481,  # API, expected to be dense
    1110,  # Click and Drag, expected to be unsuitable/interactive-scale
)


def main() -> int:
    output_dir = ROOT / "samples" / "xkcd_experimental"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    preview_paths: list[Path] = []

    for number in SAMPLE_IDS:
        comic = fetch_xkcd_comic(number)
        image = download_comic_image(comic)
        suitability = analyze_xkcd_image(image)
        row: dict[str, object] = {
            "number": comic.number,
            "title": comic.title,
            "comic_url": comic.comic_url,
            "image_url": comic.image_url,
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
        }
        if suitability.suitable:
            render = render_xkcd_card(comic, image, suitability)
            paths = write_xkcd_render(render, output_dir)
            row["paths"] = {key: str(path) for key, path in paths.items()}
            preview_paths.append(paths["preview"])
        else:
            card = _render_rejection_card(comic, suitability)
            reject_path = output_dir / f"xkcd_{comic.number:04d}_rejected.png"
            card.save(reject_path)
            row["paths"] = {"rejection": str(reject_path)}
            preview_paths.append(reject_path)
        rows.append(row)

    (output_dir / "summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _write_contact_sheet(preview_paths, output_dir / "contact_sheet.png")
    print(f"Wrote xkcd samples to {output_dir}")
    for row in rows:
        state = "ACCEPT" if row["suitable"] else "REJECT"
        print(f"{state} #{row['number']} {row['title']} score={row['score']} reasons={row['reasons']}")
    return 0


def _render_rejection_card(comic: XkcdComic, suitability) -> Image.Image:
    image = Image.new("RGB", (400, 300), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 399, 299), outline=(209, 25, 32), width=4)
    draw.text((18, 18), f"xkcd #{comic.number}: {comic.title}", fill=(17, 17, 17))
    draw.text((18, 52), "Not suitable for Ditherloom display", fill=(209, 25, 32))
    y = 84
    for reason in suitability.reasons[:5]:
        draw.text((18, y), f"- {reason}", fill=(17, 17, 17))
        y += 28
    draw.text((18, 266), "xkcd / Randall Munroe | CC BY-NC 2.5", fill=(209, 25, 32))
    return image


def _write_contact_sheet(paths: list[Path], output_path: Path) -> None:
    thumbs = []
    for path in paths:
        thumb = Image.open(path).convert("RGB")
        thumb.thumbnail((200, 150), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (200, 150), (255, 255, 255))
        canvas.paste(thumb, ((200 - thumb.width) // 2, (150 - thumb.height) // 2))
        thumbs.append(canvas)
    cols = 2
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 200, rows * 150), (225, 221, 209))
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % cols) * 200, (index // cols) * 150))
    sheet.save(output_path)


if __name__ == "__main__":
    raise SystemExit(main())
