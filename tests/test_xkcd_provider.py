import sys
import types
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)
ditherloom_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon")
ditherloom_package.__path__ = [str(ROOT / "custom_components" / "ditherloom_suite_ha_addon")]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon", ditherloom_package)

from custom_components.ditherloom_suite_ha_addon.renderer.pack import PACKED_LENGTH
from custom_components.ditherloom_suite_ha_addon.renderer.palette import TEMPLATE_COLOURS
from custom_components.ditherloom_suite_ha_addon.xkcd_provider import (
    XkcdComic,
    analyze_xkcd_image,
    render_xkcd_card,
)


def test_xkcd_accepts_landscape_up_to_three_panels():
    image = Image.new("RGB", (900, 320), "white")
    draw = ImageDraw.Draw(image)
    for offset in (0, 300, 600):
        draw.rectangle((offset + 15, 20, offset + 285, 300), outline="black", width=5)
        draw.line((offset + 45, 250, offset + 240, 80), fill="black", width=6)

    suitability = analyze_xkcd_image(image)

    assert suitability.suitable
    assert suitability.panel_count <= 3
    assert "three landscape panels" in suitability.supported_features


def test_xkcd_rejects_four_panel_or_tall_comics():
    image = Image.new("RGB", (1000, 360), "white")
    draw = ImageDraw.Draw(image)
    for offset in (0, 250, 500, 750):
        draw.rectangle((offset + 15, 30, offset + 235, 330), outline="black", width=5)

    suitability = analyze_xkcd_image(image)

    assert not suitability.suitable
    assert any("maximum is 3" in reason for reason in suitability.reasons)

    tall = Image.new("RGB", (300, 850), "white")
    draw = ImageDraw.Draw(tall)
    draw.rectangle((20, 20, 280, 830), outline="black", width=6)
    tall_suitability = analyze_xkcd_image(tall)

    assert not tall_suitability.suitable
    assert any("too tall" in reason for reason in tall_suitability.reasons)


def test_xkcd_rejects_poorly_reproducible_colour_art():
    image = Image.new("RGB", (640, 320), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 620, 300), fill=(80, 160, 230))
    draw.line((80, 260, 560, 60), fill="black", width=8)

    suitability = analyze_xkcd_image(image)

    assert not suitability.suitable
    assert any("poorly reproducible colour" in reason for reason in suitability.reasons)
    assert "blue" in suitability.dominant_poor_colour_families or "cyan" in suitability.dominant_poor_colour_families


def test_xkcd_accepts_panel_safe_warm_colour_art():
    image = Image.new("RGB", (640, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 24, 616, 276), outline="black", width=5)
    draw.rectangle((80, 80, 560, 220), fill=(230, 106, 26))
    draw.line((120, 230, 520, 70), fill="black", width=8)

    suitability = analyze_xkcd_image(image)
    comic = XkcdComic(
        number=2,
        title="Warm Colour",
        alt="",
        image_url="https://imgs.xkcd.com/comics/warm_colour.png",
        comic_url="https://xkcd.com/2/",
        published="2006-01-02",
    )
    render = render_xkcd_card(comic, image, suitability)

    assert suitability.suitable
    assert suitability.safe_colour_pixel_ratio > 0.10
    assert suitability.poor_colour_pixel_ratio == 0
    assert any("panel-safe warm colour" in feature for feature in suitability.supported_features)
    assert {2, 3}.issubset(set(render.artifact.codes))


def test_xkcd_rejects_tiny_annotation_clutter_even_when_colour_safe():
    image = Image.new("RGB", (760, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 24, 736, 276), outline="black", width=5)
    for row in range(36, 252, 18):
        for col in range(42, 720, 42):
            draw.line((col, row, col + 22, row + 8), fill=(209, 25, 32), width=2)
            draw.line((col + 7, row + 10, col + 28, row + 15), fill="black", width=1)

    suitability = analyze_xkcd_image(image)

    assert not suitability.suitable
    assert any("tiny detail" in reason or "total ink/detail" in reason for reason in suitability.reasons)


def test_xkcd_render_uses_exact_panel_colours_and_red_regular_attribution():
    comic = XkcdComic(
        number=1,
        title="Sample",
        alt="Alt text preserved in metadata.",
        image_url="https://imgs.xkcd.com/comics/sample.png",
        comic_url="https://xkcd.com/1/",
        published="2006-01-01",
    )
    image = Image.new("RGB", (640, 260), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 20, 610, 240), outline="black", width=5)
    draw.line((80, 210, 540, 70), fill="black", width=7)
    suitability = analyze_xkcd_image(image)
    render = render_xkcd_card(comic, image, suitability)

    assert render.image.size == (400, 300)
    assert len(render.artifact.packed) == PACKED_LENGTH
    assert render.artifact.metadata["license"] == "CC BY-NC 2.5"
    assert "No generic near-colour snapping is used" in render.artifact.metadata["data_transformations"]
    assert set(render.artifact.codes).issubset({0, 1, 3})

    red = TEMPLATE_COLOURS["red"].rgb
    red_pixels = [
        render.image.getpixel((x, y))
        for y in range(266, 294)
        for x in range(12, 388)
        if render.image.getpixel((x, y)) == red
    ]
    assert red_pixels
