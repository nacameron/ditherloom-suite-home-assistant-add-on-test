from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ditherloom_suite_ha_addon"
INIT = COMPONENT / "__init__.py"
BUTTON = COMPONENT / "button.py"
SENSOR = COMPONENT / "sensor.py"
UPDATE = COMPONENT / "update.py"
WEATHER_ART = COMPONENT / "assets" / "weather_art"


def test_home_assistant_brand_assets_are_packaged():
    for name in (
        "icon.png",
        "logo.png",
        "brand/icon.png",
        "brand/icon@2x.png",
        "brand/dark_icon.png",
        "brand/dark_icon@2x.png",
        "brand/logo.png",
        "brand/logo@2x.png",
        "brand/dark_logo.png",
        "brand/dark_logo@2x.png",
    ):
        path = COMPONENT / name
        assert path.exists()
        assert path.stat().st_size > 0


def test_update_platform_accepts_artwork_sized_release_downloads():
    update_source = UPDATE.read_text(encoding="utf-8")

    assert "from pathlib import Path" in update_source
    assert "MAX_ZIPBALL_BYTES = 96 * 1024 * 1024" in update_source
    assert "MAX_ZIPBALL_BYTES = 30 * 1024 * 1024" not in update_source


def test_weather_backdrops_are_packaged_at_panel_resolution():
    total_size = 0
    for path in WEATHER_ART.glob("*.png"):
        total_size += path.stat().st_size
        with Image.open(path) as image:
            assert image.size == (400, 300)

    assert total_size < 5 * 1024 * 1024


def test_sync_wifi_button_is_not_created_and_stale_entity_is_removed():
    button_source = BUTTON.read_text(encoding="utf-8")
    init_source = INIT.read_text(encoding="utf-8")

    assert "Synchronise Wi-Fi wake window" not in button_source
    assert "Synchronise Wi-Fi wake window" not in init_source
    assert "Send weather to frame" not in button_source
    assert "Send weather to frame" not in init_source
    assert "Frame schedule status" not in init_source
    assert "STALE_FRONTEND_ENTITY_NAMES" in init_source
    assert "sync_wifi_wake_window" in init_source
    assert "send_weather_to_frame" in init_source
    assert "frame_schedule_status" in init_source
    assert "list(registry.entities.values())" in init_source
    assert "entity_entry.domain != \"button\"" not in init_source
    assert "_is_stale_frontend_entity" in init_source
    assert "registry.async_remove(entity_entry.entity_id)" in init_source


def test_handshake_sensor_exposes_frame_schedule_config():
    sensor_source = SENSOR.read_text(encoding="utf-8")

    assert '"frame_schedule_enabled"' in sensor_source
    assert '"frame_wake_window_seconds"' in sensor_source
    assert '"frame_max_jobs_per_wake"' in sensor_source
    assert '"frame_ha_slot_csv"' in sensor_source
    assert '"frame_ha_rotation_enabled"' in sensor_source
    assert '"content_rendered_at"' in sensor_source
    assert '"content_rendered_provider_id"' in sensor_source
    assert '"content_rendered_provider_name"' in sensor_source
    assert '"content_rendered_source"' in sensor_source
    assert '"content_rendered_source_name"' in sensor_source
    assert '"content_rendered_source_url"' in sensor_source
    assert '"content_rendered_attribution"' in sensor_source
    assert '"content_rendered_attribution_url"' in sensor_source
    assert '"content_rendered_license"' in sensor_source
    assert '"content_rendered_license_url"' in sensor_source
    assert '"content_rendered_data_transformations"' in sensor_source
    assert '"content_rendered_secondary_attribution"' in sensor_source
    assert '"content_rendered_content_id"' in sensor_source
    assert '"content_rendered_crc32"' in sensor_source
    assert '"frame_content_last_delivered_at"' in sensor_source
    assert '"frame_content_last_delivered_count"' in sensor_source
    assert '"frame_content_last_delivered_slots"' in sensor_source
    assert '"frame_content_last_delivered_crc32"' in sensor_source
    assert '"frame_content_last_delivered_content_ids"' in sensor_source
    assert '"frame_content_last_delivered_provider_ids"' in sensor_source
    assert '"frame_content_last_delivered_provider_names"' in sensor_source
    assert '"frame_content_last_delivered_attributions"' in sensor_source
    assert '"frame_content_last_delivered_licenses"' in sensor_source
    assert '"frame_awake_last_delivered_sources"' in sensor_source
    assert '"frame_awake_last_delivered_attributions"' in sensor_source
    assert '"frame_awake_last_delivered_licenses"' in sensor_source
    assert '"frame_content_last_delivered_summary"' in sensor_source
    assert '"frame_awake_last_delivered_jobs"' in sensor_source
    assert '"frame_awake_last_delivery_summary"' in sensor_source
    assert '"frame_awake_last_failed_at"' in sensor_source
    assert '"frame_awake_last_completion_command"' in sensor_source
    assert '"frame_awake_last_completion_sent_at"' in sensor_source
    assert '"frame_awake_last_completion_response"' in sensor_source
    assert '"frame_awake_last_completion_ok"' in sensor_source
    assert '"frame_sleeping_expected_after_completion"' in sensor_source
    assert "DitherloomDataAttributionSensor" in sensor_source
    assert '"Data attribution"' in sensor_source
    assert "from homeassistant.util import dt as dt_util" in sensor_source
    assert "_state_time_label" in sensor_source
    assert "dt_util.as_local(value)" in sensor_source
    assert 'return f"frame awake {_state_time_label(awake_at, self.hass)}"' in sensor_source
    assert 'return f"delivered {count} job' in sensor_source
    assert "Sent {count} job" in sensor_source


def test_backend_attribution_sensor_is_always_visible():
    sensor_source = SENSOR.read_text(encoding="utf-8")

    assert "DitherloomDataAttributionSensor(coordinator, entry)" in sensor_source
    assert "class DitherloomDataAttributionSensor" in sensor_source
    assert 'self._attr_unique_id = f"{entry.entry_id}_data_attribution"' in sensor_source
    assert 'return "Open-Meteo Weather; Ditherloom local sun/moon"' in sensor_source
    assert '"weather_provider": "Open-Meteo"' in sensor_source
    assert '"weather_attribution": OPEN_METEO_ATTRIBUTION' in sensor_source
    assert '"weather_attribution_url": OPEN_METEO_ATTRIBUTION_URL' in sensor_source
    assert '"weather_license": OPEN_METEO_LICENSE' in sensor_source
    assert '"weather_license_url": OPEN_METEO_LICENSE_URL' in sensor_source
    assert '"place_lookup_provider": "OpenStreetMap / Nominatim"' in sensor_source
    assert '"place_lookup_attribution": NOMINATIM_ATTRIBUTION' in sensor_source
    assert '"place_lookup_attribution_url": NOMINATIM_ATTRIBUTION_URL' in sensor_source
    assert '"place_lookup_license": NOMINATIM_LICENSE' in sensor_source
    assert '"place_lookup_license_url": NOMINATIM_LICENSE_URL' in sensor_source
    assert '"sun_provider": "Ditherloom local solar calculation"' in sensor_source
    assert '"moon_provider": "Ditherloom local moon calculation"' in sensor_source
    assert '"visible_card_attribution": "Weather cards show OPEN-METEO. Sun and moon cards show DITHERLOOM."' in sensor_source
    assert '"audit_note": "These diagnostic attribution fields are fixed compliance metadata' in sensor_source


def test_renderer_cache_is_versioned():
    init_source = (ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py").read_text(encoding="utf-8")
    assert "CARD_RENDERER_VERSION" in init_source
    assert 'CARD_RENDERER_VERSION = "luxe-0.1.69"' in init_source
    assert 'metadata["card_renderer_version"] = CARD_RENDERER_VERSION' in init_source
    assert 'metadata.get("card_renderer_version") != CARD_RENDERER_VERSION' in init_source


def test_frame_awake_uses_prerendered_cache_only():
    init_source = INIT.read_text(encoding="utf-8")
    frame_awake_start = init_source.index("async def async_handle_frame_awake")
    frame_awake_end = init_source.index("async def async_deliver_cached_content_to_announced_frame", frame_awake_start)
    frame_awake_source = init_source[frame_awake_start:frame_awake_end]
    sync_jobs_start = init_source.index("async def _frame_sync_jobs")
    sync_jobs_end = init_source.index("def _provider_needs_frame_sync", sync_jobs_start)
    sync_jobs_source = init_source[sync_jobs_start:sync_jobs_end]

    assert 'async_refresh_content_payload(reason="frame_awake")' not in frame_awake_source
    assert "async_render_provider_to_cache(provider)" not in sync_jobs_source
    assert "Pre-rendered Home Assistant content is missing or stale" in sync_jobs_source
    assert "frame_awake_missing_cached_providers" in sync_jobs_source


def test_weather_luxe_uses_full_background_art():
    cards_source = (COMPONENT / "renderer" / "cards.py").read_text(encoding="utf-8")
    modern_start = cards_source.index("def render_modern_weather_card")
    modern_end = cards_source.index("def _render_luxe_weather_card", modern_start)
    modern_source = cards_source[modern_start:modern_end]
    paste_start = cards_source.index("def _paste_luxe_weather_art")
    paste_end = cards_source.index("def _draw_luxe_weather_tile", paste_start)
    paste_source = cards_source[paste_start:paste_end]

    assert "render_weather_card(" not in modern_source
    assert "image = _render_luxe_weather_card(data)" in modern_source
    assert 'ImageOps.grayscale(image).convert("RGB")' in modern_source
    assert "art.thumbnail" not in paste_source
    assert "WIDTH / artwork.width" in paste_source
    assert "HEIGHT / artwork.height" in paste_source
    assert "image.paste(resized.crop" in paste_source


def test_luxe_cards_use_fixed_large_fonts_not_box_fitted_fonts():
    cards_source = (COMPONENT / "renderer" / "cards.py").read_text(encoding="utf-8")
    left_start = cards_source.index("def _draw_luxe_text_left")
    left_end = cards_source.index("def _draw_luxe_text_right", left_start)
    right_start = left_end
    right_end = cards_source.index("def _draw_solid_palette_text", right_start)
    left_source = cards_source[left_start:left_end]
    right_source = cards_source[right_start:right_end]
    weather_start = cards_source.index("def _render_luxe_weather_card")
    weather_end = cards_source.index("def _paste_luxe_weather_art", weather_start)
    weather_source = cards_source[weather_start:weather_end]

    assert "_fit_font(" not in left_source
    assert "_fit_font(" not in right_source
    assert "_truncate_for_width" not in cards_source
    assert "font = _fit_ui_font(value" in left_source
    assert "font = _fit_ui_font(value" in right_source
    assert "_draw_luxe_location_text(draw, (23, 15, 272, 45)" in weather_source
    assert "_draw_luxe_text_left(draw, (28, 199, 158, 247), temperature, 66" in weather_source
    assert "_draw_luxe_text_left(draw, (247, 179, 377, 211), condition, 26" in weather_source
    assert "_draw_luxe_text_left(draw, (x1 + 9, y1 + 20, x2 - 8, y2 - 6), value, 29" in cards_source


def test_luxe_renderer_uses_bundled_font_and_protected_text_threshold():
    cards_source = (COMPONENT / "renderer" / "cards.py").read_text(encoding="utf-8")
    fonts_dir = COMPONENT / "assets" / "fonts"

    assert (fonts_dir / "BarlowCondensed-Bold.otf").exists()
    assert (fonts_dir / "BarlowCondensed-Regular.otf").exists()
    assert (fonts_dir / "OFL-Barlow.txt").exists()
    assert 'FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"' in cards_source
    assert 'str(FONT_DIR / "BarlowCondensed-Bold.otf")' in cards_source
    assert 'str(FONT_DIR / "BarlowCondensed-Regular.otf")' in cards_source
    assert "TEXT_ALPHA_THRESHOLD = 32" in cards_source
    assert "pixel >= TEXT_ALPHA_THRESHOLD" in cards_source
    assert "ImageFont.load_default()" not in cards_source


def test_weather_options_make_open_meteo_attribution_visible():
    strings_source = (COMPONENT / "strings.json").read_text(encoding="utf-8")
    translations_source = (COMPONENT / "translations" / "en.json").read_text(encoding="utf-8")

    for source in (strings_source, translations_source):
        assert "Weather data: Open-Meteo (https://open-meteo.com/), CC BY 4.0." in source
        assert "Place lookup: OpenStreetMap/Nominatim (https://www.openstreetmap.org/copyright), ODbL." in source


def test_sun_moon_cards_use_source_attribution_label():
    cards_source = (COMPONENT / "renderer" / "cards.py").read_text(encoding="utf-8")

    assert "_source_label(data.attribution)" in cards_source
    assert 'return "LOCAL CALC"' not in cards_source
    assert 'return "DITHERLOOM"' in cards_source
    assert 'return "OPEN-METEO"' in cards_source


def test_provider_attribution_metadata_is_recorded_for_backend_compliance():
    init_source = INIT.read_text(encoding="utf-8")
    open_meteo_source = (COMPONENT / "open_meteo.py").read_text(encoding="utf-8")

    assert 'OPEN_METEO_LICENSE = "CC BY 4.0"' in open_meteo_source
    assert 'OPEN_METEO_ATTRIBUTION_URL = "https://open-meteo.com/"' in open_meteo_source
    assert 'NOMINATIM_ATTRIBUTION_URL = "https://www.openstreetmap.org/copyright"' in open_meteo_source
    assert 'NOMINATIM_LICENSE = "ODbL"' in open_meteo_source
    assert 'metadata["source_name"] = "Open-Meteo"' in init_source
    assert 'metadata["license"] = OPEN_METEO_LICENSE' in init_source
    assert 'metadata["license_url"] = OPEN_METEO_LICENSE_URL' in init_source
    assert 'metadata["secondary_attribution"] = NOMINATIM_ATTRIBUTION' in init_source
    assert 'metadata["source_name"] = "Ditherloom local solar calculation"' in init_source
    assert 'metadata["source_name"] = "Ditherloom local moon calculation"' in init_source
    assert '"content_source": metadata.get("source")' in init_source
    assert '"attribution": metadata.get("attribution")' in init_source
    assert '"license_url": metadata.get("license_url")' in init_source
    assert '"frame_content_last_delivered_attributions"' in init_source
    assert '"frame_content_last_delivered_licenses"' in init_source
