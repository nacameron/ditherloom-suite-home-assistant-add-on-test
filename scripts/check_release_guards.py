from __future__ import annotations

from pathlib import Path
import ast
import json
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("Pic" + "Pak", "pic" + "pak", "PIC" + "PAK")
SKIP_PARTS = {".git", ".venv", ".pytest_cache", "__pycache__", "data"}
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".dockerfile",
}


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {"Dockerfile", "LICENSE"}


def fail(message: str) -> None:
    print(f"release guard failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_branding() -> None:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        rel = path.relative_to(ROOT)
        rel_text = str(rel)
        if any(token in rel_text for token in FORBIDDEN):
            hits.append(rel_text)
            continue
        if path.is_file() and is_text_file(path):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in FORBIDDEN:
                if token in text:
                    hits.append(f"{rel_text}: contains old brand token")
                    break
    if hits:
        fail("old Ditherloom predecessor branding found:\n" + "\n".join(hits[:50]))


def check_licenses() -> None:
    license_path = ROOT / "LICENSE.md"
    notices_path = ROOT / "THIRD_PARTY_NOTICES.md"
    privacy_path = ROOT / "PRIVACY.md"
    if not license_path.exists():
        fail("LICENSE.md is missing")
    if not notices_path.exists():
        fail("THIRD_PARTY_NOTICES.md is missing")
    if not privacy_path.exists():
        fail("PRIVACY.md is missing")
    license_text = license_path.read_text(encoding="utf-8")
    notices_text = notices_path.read_text(encoding="utf-8")
    privacy_text = privacy_path.read_text(encoding="utf-8")
    for required in ("Polycom 1", "Neil Cameron", "third-party"):
        if required not in license_text:
            fail(f"LICENSE.md missing required text: {required}")
    license_text_lower = license_text.lower()
    for required in ("custom weather-card images", "custom templates", "custom device-screen graphics"):
        if required not in license_text_lower:
            fail(f"LICENSE.md missing custom graphics copyright text: {required}")
    for required in ("FastAPI", "Uvicorn", "Pillow", "Eclipse Paho MQTT", "python-multipart", "Open-Meteo"):
        if required not in notices_text:
            fail(f"THIRD_PARTY_NOTICES.md missing required component: {required}")
    for required in ("Open-Meteo", "Nominatim/OpenStreetMap", "place name", "latitude", "longitude"):
        if required not in privacy_text:
            fail(f"PRIVACY.md missing required text: {required}")


def check_no_generated_cache_files() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    generated = [
        path
        for path in tracked
        if "__pycache__" in Path(path).parts or Path(path).suffix in {".pyc", ".pyo"}
    ]
    if generated:
        fail("generated Python cache files must not be committed:\n" + "\n".join(generated[:50]))


def _eval_constant(node: ast.AST, values: dict[str, int]) -> int:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, ast.BinOp):
        left = _eval_constant(node.left, values)
        right = _eval_constant(node.right, values)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
    raise ValueError(ast.dump(node))


def _load_int_constants(path: Path) -> dict[str, int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                values[node.targets[0].id] = _eval_constant(node.value, values)
            except ValueError:
                continue
    return values


def check_device_spec_alignment() -> None:
    const_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "const.py"
    pack_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "renderer" / "pack.py"
    init_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py"

    constants = _load_int_constants(const_path)
    expected = {
        "DEVICE_FRAME_WIDTH": 400,
        "DEVICE_FRAME_HEIGHT": 300,
        "DEVICE_PIXEL_COUNT": 120000,
        "DEVICE_PACKED_PAYLOAD_BYTES": 30000,
        "DEVICE_SLOT_COUNT": 446,
        "DEVICE_SLOT_STRIDE_BYTES": 32768,
        "DEVICE_SOURCE_METADATA_HEADER_BYTES": 16,
        "DEVICE_SOURCE_METADATA_PAYLOAD_BYTES": 2752,
        "DEVICE_WIFI_B64WRITE_CHUNK_BYTES": 1024,
        "DEVICE_WIFI_COMMAND_MAX_CHARS": 2048,
        "DEFAULT_TARGET_SLOT": 445,
    }
    for name, value in expected.items():
        if constants.get(name) != value:
            fail(f"device spec constant drifted: {name} expected {value}, got {constants.get(name)}")

    pack_text = pack_path.read_text(encoding="utf-8")
    for required in (
        "PACKED_LENGTH = DEVICE_PACKED_PAYLOAD_BYTES",
        'DEVICE_ORIENTATION_TRANSFORM = "flip_vertical_per_device_packet_spec"',
        "Image.Transpose.FLIP_TOP_BOTTOM",
        '"slot_stride_bytes": DEVICE_SLOT_STRIDE_BYTES',
        '"source_metadata_payload_bytes": DEVICE_SOURCE_METADATA_PAYLOAD_BYTES',
        '"device_orientation_transform": DEVICE_ORIENTATION_TRANSFORM',
        "ppbin_path.write_bytes(artifact.packed)",
    ):
        if required not in pack_text:
            fail(f"renderer packer missing device-spec guard/text: {required}")

    init_text = init_path.read_text(encoding="utf-8")
    for required in (
        "len(packed) != DEVICE_PACKED_PAYLOAD_BYTES",
        "slot < 1 or slot > DEVICE_SLOT_COUNT",
        "DEVICE_WIFI_B64WRITE_CHUNK_BYTES",
        "len(command) > DEVICE_WIFI_COMMAND_MAX_CHARS",
        "0x{crc32}",
        "WIFI_BANNER_PREFIX",
        "every command response is read one line late",
    ):
        if required not in init_text:
            fail(f"Gateway sender missing device-spec guard/text: {required}")


def check_update_platform() -> None:
    init_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py"
    update_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "update.py"
    manifest_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "manifest.json"

    if not update_path.exists():
        fail("Home Assistant update platform is missing")

    init_text = init_path.read_text(encoding="utf-8")
    update_text = update_path.read_text(encoding="utf-8")
    manifest_text = manifest_path.read_text(encoding="utf-8")

    for required in (
        '"update"',
        "async_forward_entry_setups(entry, PLATFORMS)",
    ):
        if required not in init_text:
            fail(f"Home Assistant setup missing update platform route/text: {required}")

    for required in (
        "UpdateEntity",
        "SCAN_INTERVAL = timedelta(minutes=30)",
        "releases/latest",
        "async_get_clientsession",
        "UpdateEntityFeature.RELEASE_NOTES",
        "UpdateEntityFeature.INSTALL",
        "async_install",
        "_install_release_zipball",
    ):
        if required not in update_text:
            fail(f"update platform missing release-check route/text: {required}")

    init_required = (
        "HAROTATION",
        "_query_gateway_ha_rotation",
        "_parse_harotation_response",
        "frame_ha_config",
        "haSlotCsv",
        "X-Home-Assistant-Token",
        "haAccessToken",
        "provider_slot_map",
    )
    for required in init_required:
        if required not in init_text:
            fail(f"runtime missing HA lane/rotation route/text: {required}")

    for forbidden in (
        "_set_gateway_ha_rotation",
        "_disable_gateway_ha_rotation",
        "_harotation_on_response_ok",
        "HAROTATION off",
    ):
        if forbidden in init_text:
            fail(f"runtime must not apply HA rotation from Home Assistant: {forbidden}")

    if '"version": "0.1.43"' not in manifest_text:
        fail("manifest version was not bumped to 0.1.43")


def check_public_repo_single_version() -> None:
    manifest_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_tag = f"v{manifest['version']}"

    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if "ditherloom-suite-home-assistant-add-on-test" not in remote:
        return

    releases = subprocess.run(
        ["gh", "release", "list", "--repo", "nacameron/ditherloom-suite-home-assistant-add-on-test", "--limit", "100"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if len(releases) != 1 or not releases[0].startswith(f"{expected_tag}\t"):
        fail(f"public GitHub repo must expose exactly one release: {expected_tag}")

    tags_output = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", "v*"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    tags = sorted(
        line.split("refs/tags/", 1)[1]
        for line in tags_output
        if "refs/tags/" in line and not line.endswith("^{}")
    )
    if tags != [expected_tag]:
        fail(f"public GitHub repo must expose exactly one version tag: {expected_tag}, got {tags}")


def check_weather_renderer_options() -> None:
    const_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "const.py"
    flow_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "config_flow.py"
    init_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py"
    button_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "button.py"
    services_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "services.yaml"
    strings_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "strings.json"
    cards_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "renderer" / "cards.py"
    open_meteo_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "open_meteo.py"

    checks = {
        const_path: (
            'CONF_DISPLAY_MODE = "display_mode"',
            'DISPLAY_MODE_COLOUR = "colour"',
            'DISPLAY_MODE_MONO = "mono"',
            "DEFAULT_DISPLAY_MODE = DISPLAY_MODE_COLOUR",
            'CONF_TEMPERATURE_UNIT = "temperature_unit"',
            'CONF_WIND_SPEED_UNIT = "wind_speed_unit"',
            'TEMPERATURE_UNIT_FAHRENHEIT = "fahrenheit"',
            'WIND_SPEED_UNIT_MPH = "mph"',
        ),
        flow_path: (
            "CONF_DISPLAY_MODE",
            "vol.In([DISPLAY_MODE_COLOUR, DISPLAY_MODE_MONO])",
            "CONF_TEMPERATURE_UNIT",
            "TEMPERATURE_UNIT_FAHRENHEIT",
            "CONF_WIND_SPEED_UNIT",
            "WIND_SPEED_UNIT_MPH",
        ),
        init_path: (
            "display_mode = str(data.get(CONF_DISPLAY_MODE) or opts.get(CONF_DISPLAY_MODE, DEFAULT_DISPLAY_MODE))",
            "temperature_unit = str(data.get(CONF_TEMPERATURE_UNIT) or opts.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT))",
            "wind_speed_unit = str(data.get(CONF_WIND_SPEED_UNIT) or opts.get(CONF_WIND_SPEED_UNIT, DEFAULT_WIND_SPEED_UNIT))",
            'metadata["temperature_unit"] = temperature_unit',
            'metadata["wind_speed_unit"] = wind_speed_unit',
            "render_modern_weather_card(card_data, colour_mode=display_mode)",
            'metadata["display_mode"] = display_mode',
            'PLATFORMS = ["sensor", "update", "button", "image"]',
            'CONF_UPDATE_INTERVAL_MINUTES',
            'DEFAULT_UPDATE_INTERVAL_MINUTES',
            'CONF_WAKE_WINDOW_SECONDS',
            "async_track_time_interval",
            "_schedule_weather_refresh",
            "_handle_weather_refresh",
            "async_refresh_weather_payload",
            "weather_refresh_next_at",
            "weather_refresh_last_success_at",
            "DitherloomFrameAwakeView",
            "DitherloomFrameSleepingView",
            "async_handle_frame_awake",
            "async_handle_frame_sleeping",
            "async_deliver_cached_weather_to_announced_frame",
            '"mode": "gateway_push"',
            "frame_awake_last_success_at",
            "frame_sleeping_last_received_at",
            "_create_notification",
            '"persistent_notification"',
            "async_run_weather_action",
            '"wake_window_seconds"',
        ),
        button_path: (
            "async_run_weather_action",
            'action="render weather"',
        ),
        services_path: (
            "temperature_unit:",
            "fahrenheit",
            "wind_speed_unit:",
            "mph",
        ),
        strings_path: (
            '"temperature_unit": "Temperature unit"',
            '"wind_speed_unit": "Wind speed unit"',
        ),
        cards_path: (
            "COLOUR_MODE_COLOUR = \"colour\"",
            "COLOUR_MODE_MONO = \"mono\"",
            "TOP_BAR_HEIGHT = 38",
            "BOTTOM_BAR_HEIGHT = 38",
            "WEATHER_TEMPLATE_DIR",
            "safe_400x300",
            "_load_weather_template",
            "_template_slug_for_data",
            "_render_template_weather_card",
            "bushfire_risk_day",
            "extreme_heat_day",
            "extreme_cold_day",
            "hail_storm_day",
            "high_wind_day",
            "storm_night",
            "rain_night",
            "partly_cloudy_night",
            "clear_night",
            "sunny_day",
            "render_weather_card(data: WeatherCardData, colour_mode: str = COLOUR_MODE_COLOUR)",
            "render_modern_weather_card(data: WeatherCardData, colour_mode: str = COLOUR_MODE_COLOUR)",
        ),
        open_meteo_path: (
            "NOMINATIM_REVERSE_URL",
            '"is_day"',
            "NIGHT_AWARE_CODES",
            '"temperature_unit": temperature_unit',
            '"wind_speed_unit": wind_speed_unit',
            'temperature_suffix = "F" if temperature_unit == "fahrenheit" else "C"',
            'wind_suffix = "mph" if wind_speed_unit == "mph" else "km/h"',
            "_condition_text",
            "@lru_cache(maxsize=64)",
            "REVERSE_GEOCODE_USER_AGENT",
            "Thunderstorm with hail",
            "Bushfire risk",
            "Extreme heat",
            "Extreme cold",
            "High wind",
        ),
    }
    for path, required_values in checks.items():
        text = path.read_text(encoding="utf-8")
        for required in required_values:
            if required not in text:
                fail(f"weather renderer option route missing required text in {path.name}: {required}")


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        fail(f"template asset is not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def check_weather_template_assets() -> None:
    template_root = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "assets" / "weather_templates"
    safe_root = template_root / "safe_400x300"
    manifest_path = template_root / "manifest.json"
    required_templates = (
        "sunny_day",
        "partly_cloudy_day",
        "cloudy_day",
        "fog_day",
        "rain_day",
        "storm_day",
        "clear_night",
        "partly_cloudy_night",
        "cloudy_night",
        "rain_night",
        "storm_night",
        "extreme_heat_day",
        "extreme_cold_day",
        "snow_day",
        "hail_storm_day",
        "high_wind_day",
        "bushfire_risk_day",
    )
    if not manifest_path.exists():
        fail("weather template manifest is missing")
    manifest_text = manifest_path.read_text(encoding="utf-8")
    for required in ("400", "300", "Ditherloom 30 safe colours", "copyright Neil Cameron"):
        if required not in manifest_text:
            fail(f"weather template manifest missing required text: {required}")
    for slug in required_templates:
        path = safe_root / f"{slug}_template_30safe_400x300.png"
        if not path.exists():
            fail(f"weather template asset missing: {slug}")
        if _png_dimensions(path) != (400, 300):
            fail(f"weather template asset has wrong size: {slug}")


def check_weather_packer_photo_path() -> None:
    pack_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "renderer" / "pack.py"
    pack_text = pack_path.read_text(encoding="utf-8")
    for required in (
        "ATKINSON_KERNEL",
        "closest_panel_code_and_rgb",
        "diffuse_photo_error",
        "RGB_TO_TEMPLATE_NAME.get(rgb)",
        "ordered_code(colour.recipe, x, y)",
    ):
        if required not in pack_text:
            fail(f"weather packer missing hybrid protected/photo conversion: {required}")
    forbidden = (
        "SAFE_RECIPE_DISTANCE_LIMIT",
        "nearest_recipe_template_name",
    )
    for blocked in forbidden:
        if blocked in pack_text:
            fail(f"weather packer still has global near-safe recipe snapping: {blocked}")


def check_frame_awake_handshake() -> None:
    init_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py"
    button_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "button.py"
    services_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "services.yaml"
    init_text = init_path.read_text(encoding="utf-8")
    button_text = button_path.read_text(encoding="utf-8")
    services_text = services_path.read_text(encoding="utf-8")
    for required in (
        "DitherloomFrameAwakeView(coordinator)",
        "DitherloomFrameSleepingView(coordinator)",
        "DitherloomDiscoveryView(hass)",
        'url = "/api/ditherloom/discovery"',
        '"/api/ditherloom/register-frame"',
        '"/api/ditherloom/discover-frame"',
        "async_validate_access_token",
        '"accepted": False',
        '"error": "unauthorized"',
        '"error": "not_configured"',
        '"entry_id": self.entry.entry_id',
        '"ha_url": origin',
        '"discovery_requires_auth": True',
        '"frame_awake_url": frame_awake_url',
        '"frame_sleeping_url": frame_sleeping_url',
        '"haSlotCsv": self._ha_slot_csv()',
        "_store_frame_provided_ha_config",
        "app_discovery_payload",
        '"frameAwakePath": self.frame_awake_url',
        '"frameSleepingPath": self.frame_sleeping_url',
        '"schema": "ditherloom-ha-config-v1"',
        'self.url = f"/api/ditherloom/{runtime.entry.entry_id}/frame-awake"',
        'self.url = f"/api/ditherloom/{runtime.entry.entry_id}/frame-sleeping"',
        "async_handle_frame_awake",
        "async_deliver_cached_weather_to_announced_frame",
        "async_send_to_frame_host",
        '"mode": "gateway_push"',
    ):
        if required not in init_text:
            fail(f"frame awake handshake missing required code/text: {required}")
    for forbidden in (
        "Synchronise Wi-Fi wake window",
        "async_sync_wake_window",
        "SERVICE_SYNC_WAKE_WINDOW",
        "_schedule_next_auto_send",
        "_handle_auto_send",
        "_probe_existing_gateway",
        "_read_existing_gateway_timer_config",
        "DitherloomSendWeatherButton",
        "Send weather to frame",
    ):
        if forbidden in init_text or forbidden in button_text or forbidden in services_text:
            fail(f"removed frame sync/manual-send/probe surface is still present: {forbidden}")


def check_dashboard_surface() -> None:
    button_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "button.py"
    sensor_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "sensor.py"
    image_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "image.py"
    dashboard_path = ROOT / "docs" / "DASHBOARD.md"
    if not image_path.exists():
        fail("Home Assistant preview image platform is missing")
    if not dashboard_path.exists():
        fail("dashboard documentation is missing")
    checks = {
        button_path: (
            "DitherloomRenderWeatherButton",
            "Render weather preview",
        ),
        sensor_path: (
            "EntityCategory.DIAGNOSTIC",
            "DeviceInfo",
            "Last job status",
            "DitherloomFrameScheduleSensor",
            "Frame handshake status",
            "async_add_listener",
            "weather_refresh_next_at",
            "frame_awake_last_received_at",
        ),
        image_path: (
            "ImageEntity",
            "Weather preview",
            "async_image",
            "preview_path",
        ),
        dashboard_path: (
            "picture-entity",
            "Render weather preview",
            "Frame handshake",
            "weather_refresh_next_at",
        ),
    }
    for path, required_values in checks.items():
        text = path.read_text(encoding="utf-8")
        for required in required_values:
            if required not in text:
                fail(f"dashboard surface missing required text in {path.name}: {required}")


def check_locked_render_delivery_pathway() -> None:
    init_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py"
    docs_path = ROOT / "docs" / "LOCKED_RENDER_DELIVERY_PATHWAY.md"
    if not docs_path.exists():
        fail("locked render delivery pathway documentation is missing")

    init_text = init_path.read_text(encoding="utf-8")
    doc_text = docs_path.read_text(encoding="utf-8")

    for required in (
        "async_refresh_weather_payload",
        "async_refresh_content_payload",
        "async_render_provider_to_cache",
        "async_track_time_interval",
        "_schedule_weather_refresh",
        "_handle_weather_refresh",
        "DitherloomFrameAwakeView",
        "DitherloomFrameSleepingView",
        "async_handle_frame_awake",
        "async_deliver_cached_weather_to_announced_frame",
        "_send_gateway_stage",
        "_best_effort_open_connection_idle",
        "timed out during Gateway",
        "async_send_to_frame_host",
        "manual_send_last_success_at",
        "await self.async_refresh_content_payload(reason)",
        'self.last_status = f"{provider_id}_ready"',
        'self.last_status = "frame_awake_received"',
        'self.last_status = "frame_awake_sent"',
        "_frame_sync_jobs",
        "_send_gateway_batch_jobs",
        "SETSLOTCLASS",
        "SLOTCLASS",
    ):
        if required not in init_text:
            fail(f"locked render delivery pathway missing required code/text: {required}")

    for forbidden in (
        "_probe_existing_gateway",
        "_read_existing_gateway_timer_config",
        "async_track_point_in_time",
        "_schedule_next_auto_send",
        "_handle_auto_send",
    ):
        if forbidden in init_text:
            fail(f"locked render delivery pathway contains forbidden shortcut: {forbidden}")

    for required in (
        "Locked Render Delivery Pathway",
        "refresh the weather payload on the Home Assistant interval",
        "frame wakes on its firmware schedule",
        "frame-awake",
        "send the existing packed payload",
        "Do not probe for the frame from Home Assistant",
    ):
        if required not in doc_text:
            fail(f"locked render delivery pathway documentation missing required text: {required}")


def main() -> None:
    check_branding()
    check_licenses()
    check_no_generated_cache_files()
    check_device_spec_alignment()
    check_update_platform()
    check_public_repo_single_version()
    check_weather_renderer_options()
    check_weather_template_assets()
    check_weather_packer_photo_path()
    check_frame_awake_handshake()
    check_dashboard_surface()
    check_locked_render_delivery_pathway()
    print("release guards passed")


if __name__ == "__main__":
    main()
