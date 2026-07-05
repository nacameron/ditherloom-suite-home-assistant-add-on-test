import sys
import types
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

ditherloom_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon")
ditherloom_package.__path__ = [str(ROOT / "custom_components" / "ditherloom_suite_ha_addon")]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon", ditherloom_package)

from custom_components.ditherloom_suite_ha_addon.comics_registry import (
    COMIC_PROVIDER_DIESEL_SWEETIES,
    COMIC_PROVIDER_MIMI_EUNICE,
    COMIC_PROVIDER_XKCD,
    COMICS_RENDER_CONTRACT,
    COMIC_SOURCES,
    comic_provider_ids,
    comics_framework_attributes,
)
from custom_components.ditherloom_suite_ha_addon.comics_selector import (
    ComicCandidate,
    ComicSuitability,
    select_best_comic_candidate,
)
from custom_components.ditherloom_suite_ha_addon.const import (
    COMICS_SLOT_MODE_ALTERNATE,
    COMICS_SLOT_MODE_PER_SOURCE,
    CONF_COMICS_ENABLED,
    CONF_COMICS_SLOT_MODE,
    CONF_DIESEL_SWEETIES_ENABLED,
    CONF_MIMI_EUNICE_ENABLED,
    CONF_WEATHER_ENABLED,
    CONF_XKCD_ENABLED,
)
from custom_components.ditherloom_suite_ha_addon.ha_lane import enabled_content_providers
from custom_components.ditherloom_suite_ha_addon.webcomic_provider import (
    WEBCOMIC_SOURCES,
    _prepare_sample_colour_art,
    expand_webcomic_candidates,
    render_webcomic_card,
    render_webcomic_sample_card,
)


def test_comics_registry_keeps_xkcd_on_existing_delivery_provider():
    options = {
        CONF_COMICS_ENABLED: True,
        CONF_COMICS_SLOT_MODE: COMICS_SLOT_MODE_ALTERNATE,
        CONF_WEATHER_ENABLED: True,
        CONF_XKCD_ENABLED: True,
    }

    assert COMIC_SOURCES[0].provider_id == COMIC_PROVIDER_XKCD
    assert [source.provider_id for source in COMIC_SOURCES] == [
        COMIC_PROVIDER_XKCD,
        COMIC_PROVIDER_DIESEL_SWEETIES,
        COMIC_PROVIDER_MIMI_EUNICE,
    ]
    assert comic_provider_ids(options) == ["comics"]
    assert enabled_content_providers(options) == ["open_meteo_weather", "xkcd_comic"]


def test_comics_registry_supports_future_per_comic_slot_mode():
    options = {
        CONF_COMICS_ENABLED: True,
        CONF_COMICS_SLOT_MODE: COMICS_SLOT_MODE_PER_SOURCE,
        CONF_XKCD_ENABLED: True,
    }

    attrs = comics_framework_attributes(options)

    assert comic_provider_ids(options) == ["xkcd_comic"]
    assert attrs["comics_slot_mode"] == COMICS_SLOT_MODE_PER_SOURCE
    assert attrs["enabled_comic_sources"] == ["xkcd"]
    assert "xkcd_comic provider" in attrs["framework_note"]
    assert "select_best_comic_candidate" in attrs["render_contract"]
    assert COMICS_RENDER_CONTRACT in attrs["render_contract"]


def test_comics_registry_records_source_attribution_and_licenses():
    attrs = comics_framework_attributes({})
    sources = {source["source_id"]: source for source in attrs["available_comic_sources"]}

    assert sources["diesel_sweeties"]["license"] == "CC BY-NC"
    assert sources["mimi_eunice"]["attribution"] == "Mimi & Eunice / Nina Paley | CC BY-SA"
    assert "giant_friday" not in sources
    assert "irregular_webcomic" not in sources


def test_comics_registry_supports_per_source_provider_ids():
    options = {
        CONF_COMICS_ENABLED: True,
        CONF_COMICS_SLOT_MODE: COMICS_SLOT_MODE_PER_SOURCE,
        CONF_XKCD_ENABLED: True,
        CONF_DIESEL_SWEETIES_ENABLED: True,
        CONF_MIMI_EUNICE_ENABLED: True,
    }

    assert comic_provider_ids(options) == [
        COMIC_PROVIDER_XKCD,
        COMIC_PROVIDER_DIESEL_SWEETIES,
        COMIC_PROVIDER_MIMI_EUNICE,
    ]


def test_non_xkcd_webcomics_reflow_all_panels_instead_of_clipping_one_panel():
    source = WEBCOMIC_SOURCES["mimi_eunice"]
    strip = Image.new("RGB", (600, 200), (255, 255, 255))
    for index, colour in enumerate(((255, 0, 0), (0, 0, 0), (255, 255, 0))):
        for x in range(index * 200 + 20, index * 200 + 180):
            for y in range(40, 160):
                strip.putpixel((x, y), colour)

    expanded = expand_webcomic_candidates(source, [_candidate_with_image("strip", strip)])

    assert len(expanded) == 1
    assert expanded[0].metadata["layout"] == "all_panels_reflow"
    assert expanded[0].metadata["left_justify_art"] is True
    assert expanded[0].image.size == (296, 292)
    assert "(all panels)" in expanded[0].title


def test_webcomic_atkinson_protects_clean_white_backgrounds():
    image = Image.new("RGB", (30, 20), (255, 255, 255))
    for x in range(5, 25):
        image.putpixel((x, 10), (0, 0, 0))

    rendered = _prepare_sample_colour_art(image, image.size)
    colours = {colour for _count, colour in rendered.getcolors(maxcolors=1_000)}

    assert (205, 206, 198) in colours
    assert (18, 20, 18) in colours
    assert colours <= {(205, 206, 198), (18, 20, 18)}


def test_webcomic_packet_render_keeps_clean_white_as_solid_panel_white():
    source = WEBCOMIC_SOURCES["diesel_sweeties"]
    image = Image.new("RGB", (160, 120), (255, 255, 255))
    for x in range(30, 130):
        image.putpixel((x, 60), (0, 0, 0))
    candidate = _candidate_with_image("white background", image)
    selection = type(
        "Selection",
        (),
        {
            "candidate": candidate,
            "suitability": _suitability(True, 90),
        },
    )()

    render = render_webcomic_card(source, selection)

    packet_pixels = [
        render.artifact.packet_debug_image.getpixel((x, y))
        for y in range(30, 260)
        for x in range(20, 280)
        if render.image.getpixel((x, y)) == (255, 255, 255)
    ]
    assert packet_pixels
    assert set(packet_pixels) == {(255, 255, 255)}


def test_webcomic_cards_include_per_comic_source_qr_and_left_attribution():
    source = WEBCOMIC_SOURCES["diesel_sweeties"]
    image = Image.new("RGB", (160, 120), (255, 255, 255))
    for x in range(30, 130):
        image.putpixel((x, 60), (0, 0, 0))
    candidate = _candidate_with_image("qr source", image)
    candidate = type(candidate)(
        source_id=candidate.source_id,
        source_name=candidate.source_name,
        title=candidate.title,
        source_url="https://www.dieselsweeties.com/archive/1234",
        image_url=candidate.image_url,
        image=candidate.image,
        metadata=candidate.metadata,
    )
    selection = type(
        "Selection",
        (),
        {
            "candidate": candidate,
            "suitability": _suitability(True, 90),
        },
    )()

    render = render_webcomic_card(source, selection)
    sample = render_webcomic_sample_card(source, selection)

    assert render.artifact.metadata["qr_url"] == candidate.source_url
    assert render.artifact.metadata["source_url"] == candidate.source_url
    assert sample.crop((316, 150, 396, 230)).getbbox() is not None
    left_text_pixels = [
        sample.getpixel((x, y))
        for y in range(14, 44)
        for x in range(316, 330)
    ]
    assert (209, 25, 32) in left_text_pixels


def test_comics_selector_rejects_unsuitable_candidates_and_returns_best_fallback():
    first = _candidate("first")
    second = _candidate("second")

    def analyzer(image):
        if image.getpixel((0, 0)) == (255, 0, 0):
            return _suitability(False, 20, "too busy")
        return _suitability(False, 70, "too tall")

    selection = select_best_comic_candidate([first, second], analyzer=analyzer)

    assert selection.candidate.title == "second"
    assert selection.suitability.score == 70
    assert len(selection.rejected) == 2


def test_comics_selector_returns_first_suitable_candidate():
    first = _candidate("first")
    second = _candidate("second")

    def analyzer(image):
        if image.getpixel((0, 0)) == (255, 0, 0):
            return _suitability(False, 20, "too busy")
        return _suitability(True, 85)

    selection = select_best_comic_candidate([first, second], analyzer=analyzer)

    assert selection.candidate.title == "second"
    assert selection.suitability.suitable
    assert len(selection.rejected) == 1


def _candidate(title: str) -> ComicCandidate:
    colour = (255, 0, 0) if title == "first" else (255, 255, 255)
    return _candidate_with_image(title, Image.new("RGB", (400, 180), colour))


def _candidate_with_image(title: str, image: Image.Image) -> ComicCandidate:
    return ComicCandidate(
        source_id="fixture",
        source_name="Fixture",
        title=title,
        source_url=f"https://example.invalid/{title}",
        image_url=f"https://example.invalid/{title}.png",
        image=image,
    )


def _suitability(suitable: bool, score: int, reason: str = "") -> ComicSuitability:
    return ComicSuitability(
        suitable=suitable,
        score=score,
        reasons=(reason,) if reason else (),
        warnings=(),
        panel_count=1,
        aspect_ratio=2.0,
        saturated_pixel_ratio=0.0,
        safe_colour_pixel_ratio=0.0,
        poor_colour_pixel_ratio=0.0,
        dominant_poor_colour_families=(),
        black_pixel_ratio=0.1,
        ink_pixel_ratio=0.1,
        small_detail_pixel_ratio=0.01,
        fitted_art_size=(376, 170),
        supported_features=("fixture",),
        unsupported_features=(),
    )
