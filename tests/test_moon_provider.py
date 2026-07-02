from datetime import date

from moon_provider import build_moon_provider_data
from renderer.cards import MoonCardData, render_moon_card
from renderer.pack import PACKED_LENGTH, WIDTH, HEIGHT, render_to_artifact


def test_moon_provider_builds_expected_daily_fields():
    data = build_moon_provider_data("-33.8688", "151.2093", "Sydney", "Australia/Sydney", date(2026, 6, 27))

    assert data.location == "Sydney"
    assert data.date_label == "27 JUN"
    assert data.phase_name
    assert data.illumination.endswith("%")
    assert data.moon_age.endswith("d")
    assert data.source_entity_id == "ditherloom.moon_phase"
    assert data.primary_label in {"MOONRISE", "MOONSET"}
    assert data.secondary_prefix in {"sets", "rose"}
    assert data.secondary_value


def test_moon_card_renders_full_background_layout():
    image = render_moon_card(
        MoonCardData(
            location="Sydney",
            date_label="27 JUN",
            phase_name="Full Moon",
            illumination="99%",
            moon_age="14.4d",
            moonrise="17:42",
            moonset="07:21",
            next_full="29 JUN",
            next_new="14 JUL",
        )
    )

    assert image.size == (WIDTH, HEIGHT)
    assert len(set(image.getdata())) > 30
    assert image.getpixel((18, 174)) != image.getpixel((200, 140))


def test_moon_card_packs_to_device_payload_length():
    image = render_moon_card(MoonCardData())
    artifact = render_to_artifact(image, "moon_phase", ["ditherloom.moon_phase"])

    assert len(artifact.packed) == PACKED_LENGTH
    assert artifact.metadata["template_name"] == "moon_phase"
    assert artifact.metadata["packed_length"] == PACKED_LENGTH
