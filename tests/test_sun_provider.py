from datetime import date
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

ditherloom_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon")
ditherloom_package.__path__ = [str(ROOT / "custom_components" / "ditherloom_suite_ha_addon")]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon", ditherloom_package)

from custom_components.ditherloom_suite_ha_addon.renderer.cards import SunCardData, render_sun_card
from custom_components.ditherloom_suite_ha_addon.renderer.pack import PACKED_LENGTH, WIDTH, HEIGHT, render_to_artifact
from sun_provider import build_sun_provider_data


def test_sun_provider_builds_expected_daily_fields():
    data = build_sun_provider_data("-33.8688", "151.2093", "Sydney", "Australia/Sydney", date(2026, 6, 27))

    assert data.location == "Sydney"
    assert data.date_label == "27 JUN"
    assert ":" in data.sunrise
    assert ":" in data.sunset
    assert "h" in data.day_length
    assert data.source_entity_id == "ditherloom.sunrise_sunset"
    assert data.primary_label in {"NEXT SUNRISE", "NEXT SUNSET"}
    assert data.secondary_prefix == "in"
    assert data.secondary_value


def test_sun_card_renders_full_background_layout():
    image = render_sun_card(
        SunCardData(
            location="Sydney",
            date_label="27 JUN",
            sunrise="07:01",
            sunset="16:56",
            civil_dawn="06:33",
            civil_dusk="17:24",
            day_length="9h 55m",
            golden_morning="07:01-08:01",
            golden_evening="15:56-16:56",
        )
    )

    assert image.size == (WIDTH, HEIGHT)
    assert len(set(image.getdata())) > 30
    assert image.getpixel((18, 174)) != image.getpixel((200, 140))


def test_sun_card_accepts_provider_payload():
    data = build_sun_provider_data("-33.8688", "151.2093", "Sydney", "Australia/Sydney", date(2026, 6, 27))
    image = render_sun_card(SunCardData(**data.__dict__))

    assert image.size == (WIDTH, HEIGHT)


def test_sun_card_packs_to_device_payload_length():
    image = render_sun_card(SunCardData())
    artifact = render_to_artifact(image, "sunrise_sunset", ["ditherloom.sunrise_sunset"])

    assert len(artifact.packed) == PACKED_LENGTH
    assert artifact.metadata["template_name"] == "sunrise_sunset"
    assert artifact.metadata["packed_length"] == PACKED_LENGTH
