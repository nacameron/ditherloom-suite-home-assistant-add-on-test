from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ditherloom_suite_ha_addon"
INIT = COMPONENT / "__init__.py"
BUTTON = COMPONENT / "button.py"
SENSOR = COMPONENT / "sensor.py"


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
    assert '"content_rendered_content_id"' in sensor_source
    assert '"content_rendered_crc32"' in sensor_source
    assert '"frame_content_last_delivered_at"' in sensor_source
    assert '"frame_content_last_delivered_count"' in sensor_source
    assert '"frame_content_last_delivered_slots"' in sensor_source
    assert '"frame_content_last_delivered_crc32"' in sensor_source
    assert '"frame_content_last_delivered_content_ids"' in sensor_source
    assert '"frame_content_last_delivered_provider_ids"' in sensor_source
    assert '"frame_content_last_delivered_provider_names"' in sensor_source
    assert '"frame_content_last_delivered_summary"' in sensor_source
    assert '"frame_awake_last_delivered_jobs"' in sensor_source
    assert '"frame_awake_last_delivery_summary"' in sensor_source
    assert '"frame_awake_last_failed_at"' in sensor_source
    assert "from homeassistant.util import dt as dt_util" in sensor_source
    assert "_state_time_label" in sensor_source
    assert "dt_util.as_local(value)" in sensor_source
    assert 'return f"frame awake {_state_time_label(awake_at, self.hass)}"' in sensor_source
    assert 'return f"delivered {count} job' in sensor_source
    assert "Sent {count} job" in sensor_source


def test_renderer_cache_is_versioned():
    init_source = (ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py").read_text(encoding="utf-8")
    assert "CARD_RENDERER_VERSION" in init_source
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
