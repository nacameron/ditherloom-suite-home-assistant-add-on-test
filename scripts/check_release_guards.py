from __future__ import annotations

from pathlib import Path
import ast
import json
import os
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
    for required in ("FastAPI", "Uvicorn", "Pillow", "Eclipse Paho MQTT", "python-multipart", "Segno", "Skyfield", "jplephem", "JPL/NASA", "Open-Meteo"):
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
    icon_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "icon.png"
    logo_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "logo.png"
    brand_icon_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "brand" / "icon.png"
    brand_logo_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "brand" / "logo.png"
    brand_paths = (
        "icon.png",
        "icon@2x.png",
        "dark_icon.png",
        "dark_icon@2x.png",
        "logo.png",
        "logo@2x.png",
        "dark_logo.png",
        "dark_logo@2x.png",
    )
    update_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "update.py"
    manifest_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "manifest.json"

    if not update_path.exists():
        fail("Home Assistant update platform is missing")
    if not icon_path.exists() or icon_path.stat().st_size <= 0:
        fail("Home Assistant integration icon.png is missing")
    if not logo_path.exists() or logo_path.stat().st_size <= 0:
        fail("Home Assistant integration logo.png is missing")
    if not brand_icon_path.exists() or brand_icon_path.stat().st_size <= 0:
        fail("Home Assistant integration brand/icon.png is missing")
    if not brand_logo_path.exists() or brand_logo_path.stat().st_size <= 0:
        fail("Home Assistant integration brand/logo.png is missing")
    for name in brand_paths:
        path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "brand" / name
        if not path.exists() or path.stat().st_size <= 0:
            fail(f"Home Assistant integration brand/{name} is missing")

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
        "from pathlib import Path",
        "MAX_ZIPBALL_BYTES = 96 * 1024 * 1024",
    ):
        if required not in update_text:
            fail(f"update platform missing release-check route/text: {required}")

    init_required = (
        "HAROTATION",
        "_query_gateway_ha_rotation",
        "_parse_harotation_response",
        "_set_gateway_ha_rotation",
        "_harotation_state_matches",
        "_harotation_on_response_ok",
        "_upload_gateway_payload(sock_file, slot, packed, crc32)",
        "_ensure_gateway_slot_is_ha(sock_file, slot)",
        'command = f"HAROTATION on',
        "frame_ha_config",
        "haSlotCsv",
        "X-Home-Assistant-Token",
        "haAccessToken",
        "import inspect",
        "result = validator(token)",
        "if inspect.isawaitable(result):",
        "result = await result",
        "return result is not None",
        "provider_slot_map",
        "CONF_FRAME_INTERVAL_MINUTES",
        '"intervalMinutes": self._frame_interval_minutes()',
        '"wakeWindowSeconds": self._effective_wake_window_seconds()',
        "updates[CONF_FRAME_INTERVAL_MINUTES] = interval_minutes",
        "updates[CONF_FRAME_HA_ROTATION_SECONDS] = seconds",
        "updates[CONF_WAKE_WINDOW_SECONDS] = wake_window_seconds",
        "sorted(parse_slot_pool(body.get(\"haSlotCsv\")))",
    )
    for required in init_required:
        if required not in init_text:
            fail(f"runtime missing HA lane/rotation route/text: {required}")

    for forbidden in (
        "_disable_gateway_ha_rotation",
        "HAROTATION off",
        "await validator(token)",
        '"ROTATION ',
        "missing_slots = [slot for slot in ha_rotation_slots if slot not in job_slots]",
        "HA rotation slots have no uploaded provider payload",
    ):
        if forbidden in init_text:
            fail(f"runtime contains forbidden rotation/auth shortcut: {forbidden}")

    if '"version": "0.1.101"' not in manifest_text:
        fail("manifest version was not bumped to 0.1.101")

    for forbidden in (
        '"mode": "frame_pull"',
        "_frame_pull_job_descriptor",
        "frame_awake_pending_pull_jobs",
        "DitherloomPayloadView",
        "payloadPath",
        "payloadUrl",
        "payload_url",
        "async_publish_job",
        "/payload/{filename}",
    ):
        if forbidden in init_text:
            fail(f"runtime contains forbidden non-Gateway HA pull route: {forbidden}")


def check_public_repo_single_version() -> None:
    github_ref = os.environ.get("GITHUB_REF", "")
    if os.environ.get("GITHUB_ACTIONS") == "true" and not github_ref.startswith("refs/tags/v"):
        return

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
    release_columns = releases[0].split("\t") if releases else []
    if len(releases) != 1 or expected_tag not in release_columns:
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
            "Weather data: Open-Meteo (https://open-meteo.com/), CC BY 4.0.",
            "Place lookup: OpenStreetMap/Nominatim (https://www.openstreetmap.org/copyright), ODbL.",
        ),
        cards_path: (
            "COLOUR_MODE_COLOUR = \"colour\"",
            "COLOUR_MODE_MONO = \"mono\"",
            "FONT_DIR = Path(__file__).resolve().parents[1] / \"assets\" / \"fonts\"",
            "BarlowCondensed-Bold.otf",
            "BarlowCondensed-Regular.otf",
            "LUXE_TEXT_BOLD = False",
            "TEXT_ALPHA_THRESHOLD = 32",
            "pixel >= TEXT_ALPHA_THRESHOLD",
            "TOP_BAR_HEIGHT = 38",
            "BOTTOM_BAR_HEIGHT = 38",
            "WEATHER_ART_DIR",
            "_template_slug_for_data",
            "_render_luxe_weather_card",
            "_paste_luxe_weather_art",
            "CURRENTLY",
            "UV",
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
    cards_text = cards_path.read_text(encoding="utf-8")
    modern_start = cards_text.index("def render_modern_weather_card")
    modern_end = cards_text.index("def _render_luxe_weather_card", modern_start)
    modern_source = cards_text[modern_start:modern_end]
    for forbidden in (
        "render_weather_card(",
    ):
        if forbidden in modern_source:
            fail(f"HA weather renderer can still route away from luxe full-backdrop layout: {forbidden}")
    for required in (
        "image = _render_luxe_weather_card(data)",
        "ImageOps.grayscale(image).convert(\"RGB\")",
    ):
        if required not in modern_source:
            fail(f"HA weather mono route must strip colour after luxe full-backdrop render: {required}")
    for forbidden in (
        "WEATHER_TEMPLATE_DIR",
        "_load_weather_template",
        "_render_template_weather_card",
        "_render_modern_weather_card_legacy",
        "weather_templates",
        "safe_400x300",
        "ImageFont.load_default()",
    ):
        if forbidden in cards_text:
            fail(f"weather renderer still contains old template path: {forbidden}")
    font_root = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "assets" / "fonts"
    for required_font in ("BarlowCondensed-Bold.otf", "BarlowCondensed-Regular.otf", "OFL-Barlow.txt"):
        if not (font_root / required_font).exists():
            fail(f"bundled renderer font asset is missing: {required_font}")


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        fail(f"template asset is not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def check_weather_art_assets() -> None:
    art_root = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "assets" / "weather_art"
    old_template_root = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "assets" / "weather_templates"
    if old_template_root.exists():
        fail("old weather template assets are still packaged")
    required_art = (
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
    for slug in required_art:
        path = art_root / f"{slug}.png"
        if not path.exists():
            fail(f"weather art asset missing: {slug}")
        width, height = _png_dimensions(path)
        if width < 400 or height < 300:
            fail(f"weather art asset is too small: {slug}")


def check_current_sun_moon_art_assets() -> None:
    assets_root = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "assets"
    forbidden = (
        assets_root / "sun_art" / "sunrise_sunset_background.png",
        assets_root / "sun_art" / "sunrise_sunset_central.png",
        assets_root / "moon_art" / "moon_phase_background.png",
    )
    for path in forbidden:
        if path.exists():
            fail(f"old sun/moon artwork asset is still packaged: {path.name}")
    cards_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "renderer" / "cards.py"
    cards_text = cards_path.read_text(encoding="utf-8")
    for forbidden_text in ("sunrise_sunset_background", "sunrise_sunset_central", "moon_phase_background"):
        if forbidden_text in cards_text:
            fail(f"old sun/moon artwork reference remains: {forbidden_text}")


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
        "async_deliver_cached_content_after_frame_callback",
        "async_deliver_cached_weather_to_announced_frame",
        "async_send_to_frame_host",
        '"mode": "gateway_push"',
        "await asyncio.sleep(1.5)",
        "single Gateway listener before HA opens the delivery",
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
        '"mode": "frame_pull"',
        "_frame_pull_job_descriptor",
        "frame_awake_pending_pull_jobs",
        "DitherloomPayloadView",
        "payloadPath",
        "payloadUrl",
        "payload_url",
        "async_publish_job",
        "/payload/{filename}",
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
            "DitherloomDataAttributionSensor",
            "Data attribution",
            "weather_attribution_url",
            "weather_license_url",
            "place_lookup_attribution_url",
            "visible_card_attribution",
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
        "No deliverable Home Assistant content is ready",
        "frame_awake_unavailable_providers",
        "frame_awake_provider_delivery_states",
        'self.last_status = "content_refresh_partial" if failed else f"{provider_id}_ready"',
        "content_refresh_failed_providers",
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
        "_schedule_next_auto_send",
        "_handle_auto_send",
        'async_refresh_content_payload(reason="frame_awake")',
        "metadata = await self.async_render_provider_to_cache(provider)",
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
    check_weather_art_assets()
    check_current_sun_moon_art_assets()
    check_weather_packer_photo_path()
    check_frame_awake_handshake()
    check_dashboard_surface()
    check_locked_render_delivery_pathway()
    print("release guards passed")


if __name__ == "__main__":
    main()
