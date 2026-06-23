from __future__ import annotations

from pathlib import Path
import ast
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
    ):
        if required not in update_text:
            fail(f"update platform missing release-check route/text: {required}")

    if '"version": "0.1.29"' not in manifest_text:
        fail("manifest version was not bumped to 0.1.29")


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
            "render_weather_card(card_data, colour_mode=display_mode)",
            'metadata["display_mode"] = display_mode',
            'PLATFORMS = ["sensor", "update", "button", "image"]',
            'CONF_UPDATE_INTERVAL_MINUTES',
            'DEFAULT_UPDATE_INTERVAL_MINUTES',
            'CONF_WAKE_WINDOW_SECONDS',
            "async_track_point_in_time",
            "_schedule_next_auto_send",
            "_handle_auto_send",
            "AUTO_SEND_PRERENDER_LEAD_SECONDS",
            "AUTO_SEND_PROBE_INTERVAL_SECONDS",
            "AUTO_SEND_COUNTER_DRIFT_SECONDS",
            "auto_send_prerender_at",
            "auto_send_expected_wake_at",
            "auto_send_search_expires_at",
            "_probe_existing_gateway",
            "_create_notification",
            '"persistent_notification"',
            '"ha_timer_us"',
            '"auto_send_next_at"',
            '"auto_send_window_expires_at"',
            "SERVICE_SYNC_WAKE_WINDOW",
            "hass.services.async_register(DOMAIN, SERVICE_SYNC_WAKE_WINDOW, handle_sync_wake_window)",
            "async_sync_wake_window",
            "async_run_weather_action",
            "_probe_existing_gateway",
            "_read_existing_gateway_timer_config",
            '"HACONFIG"',
            '"SLEEPINFO"',
            '"frame_timer"',
            '"wake_window_seconds"',
        ),
        button_path: (
            "async_run_weather_action",
            'action="render weather"',
            'action="send weather"',
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
            "GLYPHS: dict[str, tuple[str, ...]]",
            "_draw_bitmap_text",
            "_fit_bitmap_scale",
            "_draw_stepped_fill",
            '"top_text": "black"',
            '"bottom_text": "black"',
            '"top_steps":',
            '"body_steps":',
            '"metric_accents":',
            '"symbol_shades":',
            'label_width = 22 if label.upper().startswith("PR") else 30',
            'min_value_size = 14 if label.upper().startswith("PR") else 10',
            "render_weather_card(data: WeatherCardData, colour_mode: str = COLOUR_MODE_COLOUR)",
            "_draw_bars(draw, data, colours)",
            "_draw_symbol(draw, kind, data, colours)",
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
        ),
    }
    for path, required_values in checks.items():
        text = path.read_text(encoding="utf-8")
        for required in required_values:
            if required not in text:
                fail(f"weather renderer option route missing required text in {path.name}: {required}")


def check_sync_button() -> None:
    button_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "button.py"
    if not button_path.exists():
        fail("Home Assistant sync button platform is missing")
    button_text = button_path.read_text(encoding="utf-8")
    for required in (
        "ButtonEntity",
        "EntityCategory.CONFIG",
        "Synchronise Wi-Fi wake window",
        "async_sync_wake_window",
    ):
        if required not in button_text:
            fail(f"sync button missing required text: {required}")


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
            "DitherloomSendWeatherButton",
            "Render weather preview",
            "Send weather to frame",
        ),
        sensor_path: (
            "EntityCategory.DIAGNOSTIC",
            "DeviceInfo",
            "Last job status",
            "DitherloomFrameScheduleSensor",
            "Frame schedule status",
            "async_add_listener",
            "next_auto_send",
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
            "Send weather to frame",
            "Synchronise Wi-Fi wake window",
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
        "AUTO_SEND_PRERENDER_LEAD_SECONDS = 30",
        "AUTO_SEND_PROBE_INTERVAL_SECONDS = 10",
        "AUTO_SEND_COUNTER_DRIFT_SECONDS = 300",
        "await self.async_render_weather({}, publish=True, send_to_frame=False)",
        'self.last_status = "auto_send_prerendered"',
        "async_track_point_in_time(self.hass, self._handle_auto_send, expected_wake)",
        "_probe_existing_gateway",
        "packed = await self.hass.async_add_executor_job(self.payload_path().read_bytes)",
        "await self.async_send_to_frame(packed, crc32)",
        'last_job["expires_at"] = search_expires.isoformat()',
        "if now + timedelta(seconds=AUTO_SEND_PROBE_INTERVAL_SECONDS) < search_expires:",
        "self._schedule_next_auto_send(from_time=expected_wake)",
    ):
        if required not in init_text:
            fail(f"locked render delivery pathway missing required code/text: {required}")

    for forbidden in (
        "await self.async_render_weather({}, publish=True, send_to_frame=True)",
        "self._schedule_next_auto_send(from_time=now)",
        "self._schedule_next_auto_send(from_time=fired_at)",
    ):
        if forbidden in init_text:
            fail(f"locked render delivery pathway contains forbidden shortcut: {forbidden}")

    for required in (
        "Locked Render Delivery Pathway",
        "pre-render",
        "probe the frame gateway before sending",
        "send the existing packed payload",
        "schedule the next cycle from the expected wake anchor",
        "Do not render during the frame wake window",
    ):
        if required not in doc_text:
            fail(f"locked render delivery pathway documentation missing required text: {required}")


def main() -> None:
    check_branding()
    check_licenses()
    check_no_generated_cache_files()
    check_device_spec_alignment()
    check_update_platform()
    check_weather_renderer_options()
    check_sync_button()
    check_dashboard_surface()
    check_locked_render_delivery_pathway()
    print("release guards passed")


if __name__ == "__main__":
    main()
