from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ditherloom_suite_ha_addon"
INIT = COMPONENT / "__init__.py"
BUTTON = COMPONENT / "button.py"
SENSOR = COMPONENT / "sensor.py"
UPDATE = COMPONENT / "update.py"
WEATHER_ART = COMPONENT / "assets" / "weather_art"
ASTRONOMY_ART = COMPONENT / "assets" / "astronomy_art"


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


def test_comic_sample_assets_are_packaged_at_panel_resolution():
    sample_dir = COMPONENT / "assets" / "comic_samples"
    for name in (
        "xkcd.preview.png",
        "diesel_sweeties.preview.png",
        "mimi_eunice.preview.png",
    ):
        path = sample_dir / name
        assert path.exists()
        assert path.stat().st_size > 0
        with Image.open(path) as image:
            assert image.size == (400, 300)
            colours = {colour for _count, colour in image.convert("RGB").getcolors(maxcolors=1_000_000)}
            assert (209, 25, 32) in colours
            if not name.startswith(("xkcd", "mimi_eunice")):
                assert (202, 174, 62) in colours or (164, 63, 55) in colours


def test_astrology_sign_assets_are_packaged_at_panel_resolution():
    sample_dir = COMPONENT / "assets" / "astrology_art"
    for name in (
        "astro_aries.png",
        "astro_taurus.png",
        "astro_gemini.png",
        "astro_cancer.png",
        "astro_leo.png",
        "astro_virgo.png",
        "astro_libra.png",
        "astro_scorpio.png",
        "astro_sagittarius.png",
        "astro_capricorn.png",
        "astro_aquarius.png",
        "astro_pisces.png",
    ):
        path = sample_dir / name
        assert path.exists()
        assert path.stat().st_size > 0
        with Image.open(path) as image:
            assert image.size == (400, 300)


def test_astronomy_assets_are_packaged_at_panel_resolution():
    for name in (
        "astronomy_visible_planets.png",
        "astronomy_moon_watch.png",
        "astronomy_constellation.png",
        "astronomy_tonight_sky.png",
        "astronomy_overhead.png",
    ):
        path = ASTRONOMY_ART / name
        assert path.exists()
        assert path.stat().st_size > 0
        with Image.open(path) as image:
            assert image.size == (400, 300)


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


def test_weather_forecast_border_is_packaged():
    path = WEATHER_ART / "forecast_7_day_border.png"

    assert path.exists()
    assert path.stat().st_size > 0
    with Image.open(path) as image:
        assert image.size == (400, 300)


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
    assert "sleeping_at is None or sleeping_at < delivered_at" in sensor_source
    assert "Sent {count} job" in sensor_source


def test_backend_attribution_sensor_is_always_visible():
    sensor_source = SENSOR.read_text(encoding="utf-8")

    assert "DitherloomDataAttributionSensor(coordinator, entry)" in sensor_source
    assert "class DitherloomDataAttributionSensor" in sensor_source
    assert 'self._attr_unique_id = f"{entry.entry_id}_data_attribution"' in sensor_source
    assert 'return "Open-Meteo Weather; Ditherloom local sun/moon; Comics; Daily Astrology; Astronomy"' in sensor_source
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
    assert '"xkcd_provider": "xkcd"' in sensor_source
    assert '"xkcd_attribution": "xkcd / Randall Munroe"' in sensor_source
    assert '"xkcd_license": "CC BY-NC 2.5"' in sensor_source
    assert '"pepper_carrot_provider": "Giant Friday"' not in sensor_source
    assert '"irregular_webcomic_provider": "Irregular Webcomic!"' not in sensor_source
    assert '"diesel_sweeties_provider": "Diesel Sweeties"' in sensor_source
    assert '"mimi_eunice_provider": "Mimi & Eunice"' in sensor_source
    assert '"astrology_attribution": "Ditherloom Astrology; planetary data by NASA/JPL via Skyfield"' in sensor_source
    assert '"astrology_license": "Ditherloom artwork/text; Skyfield and jplephem MIT; NASA/JPL ephemeris data retained under source terms"' in sensor_source
    assert '"astrology_skyfield": "Skyfield MIT licensed Python astronomy library"' in sensor_source
    assert '"astrology_jplephem": "jplephem MIT licensed JPL ephemeris reader"' in sensor_source
    assert '"astrology_ephemeris": "JPL/NASA ephemeris data used for planetary and lunar positions; Ditherloom does not claim copyright over NASA/JPL data."' in sensor_source
    assert '"astronomy_attribution": "Ditherloom Astronomy; planetary data by NASA/JPL via Skyfield"' in sensor_source
    assert '"astronomy_license": "Ditherloom artwork/text; Skyfield and jplephem MIT; NASA/JPL ephemeris data retained under source terms"' in sensor_source
    assert '"astronomy_skyfield": "Skyfield MIT licensed Python astronomy library"' in sensor_source
    assert '"astronomy_jplephem": "jplephem MIT licensed JPL ephemeris reader"' in sensor_source
    assert '"astronomy_ephemeris": "JPL/NASA DE421 ephemeris data used for local sky positions; Ditherloom does not claim copyright over NASA/JPL data."' in sensor_source
    assert '"astronomy_noaa_swpc": "NOAA/SWPC space-weather data for Solar Activity and Aurora Watch; public domain unless otherwise noted; Ditherloom does not claim copyright over NOAA data."' in sensor_source
    assert '"astronomy_open_meteo": "Open-Meteo cloud cover and visibility data for Astronomy View Conditions"' in sensor_source
    assert '"visible_card_attribution": "Weather cards show OPEN-METEO. Sun and moon cards show DITHERLOOM. Comic cards show source-specific red attribution and license text. Astrology cards show DITHERLOOM. Astronomy cards show DITHERLOOM plus Skyfield/JPL, Open-Meteo, or NOAA/SWPC as applicable."' in sensor_source
    assert '"audit_note": "These diagnostic attribution fields are fixed compliance metadata' in sensor_source


def test_renderer_cache_is_versioned():
    init_source = (ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py").read_text(encoding="utf-8")
    assert "CARD_RENDERER_VERSION" in init_source
    assert 'CARD_RENDERER_VERSION = "luxe-0.1.114-astronomy-centered-conditions"' in init_source
    assert 'metadata["card_renderer_version"] = CARD_RENDERER_VERSION' in init_source
    assert 'metadata.get("card_renderer_version") != CARD_RENDERER_VERSION' in init_source


def test_ha_slot_capacity_and_content_cadence_are_app_owned_in_options_ui():
    config_source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    strings_source = (COMPONENT / "strings.json").read_text(encoding="utf-8")

    setup_start = config_source.index("async def async_step_user")
    setup_end = config_source.index("@staticmethod", setup_start)
    setup_source = config_source[setup_start:setup_end]
    device_start = config_source.index("async def async_step_device")
    device_end = config_source.index("def _data", device_start)
    device_source = config_source[device_start:device_end]
    save_start = config_source.index("def _save_options_or_show")
    save_end = config_source.index("def _comic_provider_form", save_start)
    save_source = config_source[save_start:save_end]

    assert "CONF_UPDATE_INTERVAL_MINUTES" not in setup_source
    assert "CONF_UPDATE_INTERVAL_MINUTES" not in device_source
    assert "Repeating update interval minutes" not in strings_source
    assert "validate_ha_lane(" not in save_source
    assert "errors={\"base\"" not in save_source
    assert "content update cadence from the Ditherloom app/frame setup" in strings_source


def test_astrology_cache_refreshes_by_local_day_not_generic_interval_only():
    init_source = (ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py").read_text(encoding="utf-8")
    fresh_start = init_source.index("def _cached_content_is_fresh")
    fresh_end = init_source.index("def _xkcd_cache_matches_options", fresh_start)
    fresh_source = init_source[fresh_start:fresh_end]

    assert "async_track_point_in_time" in init_source
    assert "self._schedule_astrology_daily_refresh()" in init_source
    assert "def async_cancel_astrology_daily_refresh" in init_source
    assert 'next_at = now.replace(hour=0, minute=2, second=0, microsecond=0)' in init_source
    assert "if metadata.get(\"astrology_date\") != target.date().isoformat():" in fresh_source
    assert "selected_sign_for_time(" in fresh_source
    assert "return True" in fresh_source


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
    assert "No deliverable Home Assistant content is ready" in sync_jobs_source
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
    assert "_cover_image(artwork, WIDTH, HEIGHT)" in paste_source


def test_weather_forecast_cards_are_exposed_as_separate_weather_menu_items():
    const_source = (COMPONENT / "const.py").read_text(encoding="utf-8")
    lane_source = (COMPONENT / "ha_lane.py").read_text(encoding="utf-8")
    config_source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    strings_source = (COMPONENT / "strings.json").read_text(encoding="utf-8")
    renderer_source = (COMPONENT / "renderer" / "cards.py").read_text(encoding="utf-8")

    assert 'CONF_WEATHER_TODAY_TOMORROW_ENABLED = "weather_today_tomorrow_enabled"' in const_source
    assert 'CONF_WEATHER_7_DAY_ENABLED = "weather_7_day_enabled"' in const_source
    assert 'CONF_WEATHER_RADAR_ENABLED = "weather_radar_enabled"' in const_source
    assert 'CONF_WEATHER_PRECIPITATION_ENABLED = "weather_precipitation_enabled"' in const_source
    assert 'CONF_WEATHER_UV_ENABLED = "weather_uv_enabled"' in const_source
    assert 'CONF_WEATHER_WIND_ENABLED = "weather_wind_enabled"' in const_source
    assert 'PROVIDER_WEATHER_TODAY_TOMORROW = "open_meteo_today_tomorrow"' in lane_source
    assert 'PROVIDER_WEATHER_7_DAY = "open_meteo_7_day_forecast"' in lane_source
    assert 'PROVIDER_WEATHER_RADAR = "weather_radar"' in lane_source
    assert 'PROVIDER_WEATHER_PRECIPITATION = "open_meteo_precipitation"' in lane_source
    assert 'PROVIDER_WEATHER_UV = "open_meteo_uv"' in lane_source
    assert 'PROVIDER_WEATHER_WIND = "open_meteo_wind"' in lane_source
    assert '"weather_current"' in config_source
    assert '"weather_today_tomorrow"' in config_source
    assert '"weather_7_day"' in config_source
    assert '"weather_radar"' in config_source
    assert '"weather_precipitation"' in config_source
    assert '"weather_uv"' in config_source
    assert '"weather_wind"' in config_source
    assert '"weather_current": "Current Weather"' in strings_source
    assert '"weather_today_tomorrow": "Today / Tomorrow"' in strings_source
    assert '"weather_7_day": "7-Day Forecast"' in strings_source
    assert '"weather_radar": "Weather Radar"' in strings_source
    assert '"weather_precipitation": "Precipitation"' in strings_source
    assert '"weather_uv": "UV"' in strings_source
    assert '"weather_wind": "Wind"' in strings_source
    assert "https://home.openweathermap.org/api_keys" in strings_source
    assert "follow OpenWeather's current API terms" in strings_source
    assert "def render_today_tomorrow_weather_card" in renderer_source
    assert "def render_seven_day_weather_card" in renderer_source
    assert "def render_weather_radar_card" in renderer_source
    assert "def render_precipitation_graph_card" in renderer_source
    assert "def render_uv_graph_card" in renderer_source
    assert "def render_wind_graph_card" in renderer_source
    assert "draw.line(diagonal, fill=_rgb(\"bright_yellow\"), width=10)" in renderer_source
    assert "draw.line(diagonal, fill=_rgb(\"white\"), width=6)" in renderer_source
    assert 'border = _load_weather_art("forecast_7_day_border")' in renderer_source
    assert "ImageEnhance.Color(image).enhance(1.2)" in renderer_source
    assert "ImageEnhance.Contrast(image).enhance(1.2)" in renderer_source


def test_weather_metric_cards_keep_text_crisp_and_do_not_near_snap_artwork():
    renderer_source = (COMPONENT / "renderer" / "cards.py").read_text(encoding="utf-8")
    packer_source = (COMPONENT / "renderer" / "pack.py").read_text(encoding="utf-8")

    hourly_start = renderer_source.index("def _draw_hourly_bars")
    hourly_end = renderer_source.index("def _bar_fill_for_metric", hourly_start)
    hourly_source = renderer_source[hourly_start:hourly_end]

    assert "_draw_luxe_text_center_outlined" not in hourly_source
    assert 'outline=_rgb("black"), width=1' in hourly_source
    assert "font_delta=2" in renderer_source
    assert "_weather_foreground_layer()" in renderer_source
    assert "_composite_weather_foreground(" in renderer_source
    assert "_remove_template_safe_pixels_from_background(" in renderer_source
    assert "_prepare_radar_layer_image(" in renderer_source
    assert 'if metric == "uv":' in renderer_source
    assert 'if metric == "wind":' in renderer_source
    assert 'if metric == "precipitation":' in renderer_source
    assert 'return _rgb("yellow")' in renderer_source
    assert 'return _rgb("white")' in renderer_source
    assert 'return _rgb("orange")' in renderer_source
    assert 'return _rgb("red")' in renderer_source
    assert "TEMPLATE_EXACT_BLACK_WHITE_ERROR" not in packer_source
    assert "TEMPLATE_EXACT_COLOUR_ERROR" not in packer_source
    assert "_template_exact_code" not in packer_source
    assert "RGB_TO_TEMPLATE_NAME.get(rgb)" in packer_source


def test_astronomy_constellation_card_uses_bonus_constellation_copy():
    source = (COMPONENT / "astronomy_provider.py").read_text(encoding="utf-8")

    assert "drawn in panel" not in source
    assert "_bonus_constellation(" in source
    assert 'MAIN_CONSTELLATION_NAME_BOX' in source
    assert 'BONUS_LABEL_BOX' not in source
    assert '_draw_single_centered(image, MAIN_CONSTELLATION_NAME_BOX, constellation.upper()' in source
    assert '_draw_single_centered(image, BONUS_NAME_BOX, bonus.upper()' in source
    assert '_draw_single_centered(image, BONUS_LABEL_BOX, "BONUS"' not in source
    assert "BONUS_CONSTELLATION_DRAW_BOX" in source


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
    assert (fonts_dir / "Kalam-Regular.ttf").exists()
    assert (fonts_dir / "OFL-Kalam.txt").exists()
    assert 'FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"' in cards_source
    assert 'str(FONT_DIR / "BarlowCondensed-Bold.otf")' in cards_source
    assert 'str(FONT_DIR / "BarlowCondensed-Regular.otf")' in cards_source
    assert "TEXT_ALPHA_THRESHOLD = 32" in cards_source
    assert "pixel >= TEXT_ALPHA_THRESHOLD" in cards_source
    assert "ImageFont.load_default()" not in cards_source


def test_luxe_cards_use_regular_barlow_not_bold_text():
    cards_source = (COMPONENT / "renderer" / "cards.py").read_text(encoding="utf-8")
    top_start = cards_source.index("def _draw_luxe_top_identity")
    top_end = cards_source.index("def _draw_luxe_main_panel", top_start)
    main_start = top_end
    main_end = cards_source.index("def _draw_luxe_tile_row", main_start)
    weather_start = cards_source.index("def _render_luxe_weather_card")
    weather_end = cards_source.index("def _paste_luxe_weather_art", weather_start)
    tile_start = cards_source.index("def _draw_luxe_weather_tile")
    tile_end = cards_source.index("def _draw_luxe_location_text", tile_start)
    location_start = tile_end
    location_end = cards_source.index("def _weather_temperature_text", location_start)

    luxe_sources = "\n".join(
        (
            cards_source[top_start:top_end],
            cards_source[main_start:main_end],
            cards_source[weather_start:weather_end],
            cards_source[tile_start:tile_end],
            cards_source[location_start:location_end],
        )
    )

    assert "LUXE_TEXT_BOLD = False" in cards_source
    assert "bold=LUXE_TEXT_BOLD" in cards_source[location_start:location_end]
    assert "LUXE_TEXT_BOLD" in luxe_sources
    assert ", True," not in luxe_sources
    assert "bold=True" not in luxe_sources


def test_weather_options_make_open_meteo_attribution_visible():
    strings_source = (COMPONENT / "strings.json").read_text(encoding="utf-8")
    translations_source = (COMPONENT / "translations" / "en.json").read_text(encoding="utf-8")
    translations_en_gb_source = (COMPONENT / "translations" / "en-GB.json").read_text(encoding="utf-8")

    for source in (strings_source, translations_source, translations_en_gb_source):
        assert "Weather data: Open-Meteo (https://open-meteo.com/), CC BY 4.0." in source
        assert "Place lookup: OpenStreetMap/Nominatim (https://www.openstreetmap.org/copyright), ODbL." in source
        assert "Optional xkcd comics are by Randall Munroe and licensed CC BY-NC 2.5" in source


def test_xkcd_options_and_controls_are_exposed_as_opt_in_provider():
    init_source = INIT.read_text(encoding="utf-8")
    config_source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    button_source = BUTTON.read_text(encoding="utf-8")
    services_source = (COMPONENT / "services.yaml").read_text(encoding="utf-8")
    strings_source = (COMPONENT / "strings.json").read_text(encoding="utf-8")
    translations_source = (COMPONENT / "translations" / "en.json").read_text(encoding="utf-8")

    assert 'CONF_XKCD_ENABLED = "xkcd_enabled"' in (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert 'CONF_XKCD_MODE = "xkcd_mode"' in (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert 'CONF_XKCD_NUMBER = "xkcd_number"' in (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert 'CONF_XKCD_RANDOM_ATTEMPTS = "xkcd_random_attempts"' in (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert 'SERVICE_RENDER_XKCD = "render_xkcd_card"' in (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert 'SERVICE_SEND_XKCD = "send_xkcd_card"' in (COMPONENT / "const.py").read_text(encoding="utf-8")
    assert '"comics_framework", "astrology", "astronomy", "device"' in config_source
    assert '"comics_framework", "xkcd", "device"' not in config_source
    assert '"comics_pepper_carrot"' not in config_source
    assert '"comics_irregular_webcomic"' not in config_source
    assert '"comics_diesel_sweeties"' in config_source
    assert '"comics_mimi_eunice"' in config_source
    assert "async_step_comics_framework" in config_source
    assert "async_step_comics_settings" in config_source
    assert "async_step_comics_xkcd" in config_source
    assert "async_step_comics_pepper_carrot" not in config_source
    assert "async_step_comics_irregular_webcomic" not in config_source
    assert "async_step_comics_diesel_sweeties" in config_source
    assert "async_step_comics_mimi_eunice" in config_source
    assert "async_step_comics" in config_source
    assert "_comics_slot_mode_selector" in config_source
    assert "async_step_xkcd" in config_source
    assert "_xkcd_attribution_selector" in config_source
    assert 'XKCD_FORM_ENABLED = "Enable xkcd Comic"' in config_source
    assert 'XKCD_FORM_ATTRIBUTION = "Attribution - xkcd / Randall Munroe | CC BY-NC 2.5"' in config_source
    assert 'XKCD_FORM_MODE = "Comic selection"' in config_source
    assert 'XKCD_FORM_NUMBER = "Fixed comic number"' in config_source
    assert 'XKCD_FORM_ATTEMPTS = "Random search attempts"' in config_source
    assert "_xkcd_form_to_options" in config_source
    assert "default=_xkcd_number_text(data.get(CONF_XKCD_NUMBER))): str" in config_source
    assert "default=data.get(CONF_XKCD_NUMBER)): int" not in config_source
    assert "_positive_int_or_none" in config_source
    assert "xkcd / Randall Munroe | CC BY-NC 2.5" in config_source
    assert "Fixed comic number" in config_source
    assert "Random suitable comic" in config_source
    assert "xkcd_number_required" in config_source
    assert "xkcd_number_invalid" in config_source
    assert "DitherloomRenderXkcdButton" in button_source
    assert "render_xkcd_card:" in services_source
    assert "send_xkcd_card:" in services_source
    assert 'metadata["provider_id"] = "xkcd_comic"' in init_source
    assert '"xkcd_suitability"' in init_source
    assert '"xkcd_alt_text"' in init_source
    assert '"xkcd_configured_number"' in init_source
    assert '"xkcd_random_attempts"' in init_source
    translations_en_gb_source = (COMPONENT / "translations" / "en-GB.json").read_text(encoding="utf-8")
    for source in (strings_source, translations_source, translations_en_gb_source):
        assert '"comics_framework": "Comics"' in source
        assert '"astrology": "Daily Astrology"' in source
        assert '"astronomy": "Astronomy"' in source
        assert '"astronomy_visible_planets": "Visible Planets"' in source
        assert '"astronomy_moon_watch": "Moon Watch"' in source
        assert '"astronomy_constellation": "Constellation Tonight"' in source
        assert '"astronomy_tonight_sky": "Tonight' in source
        assert '"astronomy_overhead": "Planets Overhead"' in source
        assert '"astronomy_conditions": "Astronomy View Conditions"' in source
        assert '"astronomy_solar_activity": "Solar Activity"' in source
        assert '"astronomy_aurora_watch": "Aurora Watch"' in source
        assert "NOAA/SWPC" in source
        assert "Open-Meteo cloud cover and visibility data" in source
        assert '"comics_settings": "Comics enabled"' in source
        assert '"comics_xkcd": "xkcd Comic"' in source
        assert '"comics_pepper_carrot": "Giant Friday"' not in source
        assert '"comics_irregular_webcomic": "Irregular Webcomic!"' not in source
        assert '"comics_diesel_sweeties": "Diesel Sweeties"' in source
        assert '"comics_mimi_eunice": "Mimi & Eunice"' in source
        assert '"comics": "Comics"' in source
        assert '"title": "Comics enabled"' in source
        assert "Each comic source, including xkcd Comic and future comic providers, has its own page in this Comics section." in source
        assert "Comic-provider settings, including xkcd Comic, live on their own pages in this Comics section" in source
        assert '"menu_options": {' in source
        assert '"comics_enabled": "Enable Comics framework"' in source
        assert '"comics_slot_mode": "Comic slot mode"' in source
        assert '"comics_xkcd": {' in source
        assert '"xkcd": {' in source
        assert '"title": "xkcd Comic"' in source
        assert '"xkcd_enabled": "Enable xkcd Comic"' in source
        assert '"xkcd_attribution_notice": "Attribution"' in source
        assert '"xkcd_mode": "Comic selection"' in source
        assert '"xkcd_number": "Fixed comic number"' in source
        assert '"xkcd_random_attempts": "Random search attempts"' in source
        assert '"xkcd_number_invalid": "Enter a whole comic number greater than zero' in source
        assert "CC BY-NC 2.5" in source
        assert "Comics are by Randall Munroe and licensed CC BY-NC 2.5" in source
        assert "Ditherloom displays this attribution on rendered xkcd cards and stores it in metadata." in source
        assert "Sample rendered for Ditherloom" in source
        assert "{pepper_carrot_sample_image}" not in source
        assert "{irregular_webcomic_sample_image}" not in source
        assert "{diesel_sweeties_sample_image}" in source
        assert "{mimi_eunice_sample_image}" in source
        assert "Skyfield and jplephem are MIT licensed" in source
        assert "JPL/NASA ephemeris data remains NASA/JPL work and is not claimed by Ditherloom" in source


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
    assert 'metadata["source_name"] = "xkcd / Randall Munroe"' in init_source
    assert 'metadata["license"] = "CC BY-NC 2.5"' in init_source
    assert 'metadata["attribution_url"] = "https://xkcd.com/license.html"' in init_source
    assert '"content_source": metadata.get("source")' in init_source
    assert '"attribution": metadata.get("attribution")' in init_source
    assert '"license_url": metadata.get("license_url")' in init_source
    assert '"frame_content_last_delivered_attributions"' in init_source
    assert '"frame_content_last_delivered_licenses"' in init_source


def test_comics_samples_and_webcomic_rendering_keep_colour_and_red_attribution():
    config_source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    init_source = INIT.read_text(encoding="utf-8")
    webcomic_source = (COMPONENT / "webcomic_provider.py").read_text(encoding="utf-8")

    assert "DitherloomComicSampleView(coordinator)" in init_source
    assert "/comic-samples/{{filename}}" in init_source
    assert '"Cache-Control": "no-store"' in init_source
    assert "_comic_sample_markdown" in config_source
    assert "?v={INTEGRATION_VERSION}" in config_source
    assert "![{label} Ditherloom sample]" in config_source
    manifest_source = (COMPONENT / "manifest.json").read_text(encoding="utf-8")
    assert '"segno==1.6.6"' in manifest_source
    assert '"skyfield==1.54"' in manifest_source
    assert '"jplephem==2.24"' in manifest_source
    assert "_atkinson_dither_to_display_preview" in webcomic_source
    assert "_draw_right_attribution(base, draw, source, candidate.source_url)" in webcomic_source
    assert "segno.make(source_url" in webcomic_source
    assert '"qr_url": candidate.source_url' in webcomic_source
    assert "RIGHT_ATTRIBUTION_LINE_X" in webcomic_source
    assert "_draw_left_fitted_text" in webcomic_source
    assert "_is_protected_comic_white" in webcomic_source
    assert "protected as clean panel white" in webcomic_source
    assert "palette[code]" in webcomic_source


def test_third_party_notices_include_font_and_dependency_compliance_details():
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    dependency_snapshot = (ROOT / "docs" / "DEPENDENCY_LICENSE_SNAPSHOT.md")

    assert "docs/DEPENDENCY_LICENSE_SNAPSHOT.md" in notices
    assert dependency_snapshot.exists()
    assert "Copyright 2017 The Barlow Project Authors" in notices
    assert "Copyright (c) 2014, Indian Type Foundry" in notices
    assert "SIL Open Font License 1.1" in notices
    assert "Fonts are (c) Bitstream" in notices
    assert "Glyphs imported from Arev fonts are (c) Tavmjong Bah" in notices
    assert "https://dejavu-fonts.github.io/License.html" in notices

    snapshot = dependency_snapshot.read_text(encoding="utf-8")
    for required in (
        "| fastapi | 0.115.6 | MIT |",
        "| uvicorn | 0.32.1 | BSD-3-Clause |",
        "| pillow | 11.0.0 | HPND / MIT-CMU style Pillow license |",
        "| paho-mqtt | 2.1.0 | EPL-2.0 OR BSD-3-Clause |",
        "| python-multipart | 0.0.20 | Apache-2.0 |",
        "| segno | 1.6.6 | BSD-3-Clause |",
        "| skyfield | 1.54 | MIT |",
        "| jplephem | 2.24 | MIT |",
        "| pytest | 8.3.4 | MIT |",
        "| Barlow / Barlow Condensed | SIL Open Font License 1.1 |",
        "| Kalam | SIL Open Font License 1.1 |",
        "| DejaVu fonts | Bitstream Vera / Arev / public-domain DejaVu changes |",
        "| JPL/NASA ephemeris data | NASA/JPL source terms apply; Ditherloom does not claim ownership |",
    ):
        assert required in snapshot
