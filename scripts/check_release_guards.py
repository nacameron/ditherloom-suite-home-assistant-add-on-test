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
        'DEVICE_ORIENTATION_TRANSFORM = "flip_horizontal_after_v0_1_15_photo"',
        "Image.Transpose.FLIP_LEFT_RIGHT",
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
        "SCAN_INTERVAL = timedelta(hours=6)",
        "releases/latest",
        "async_get_clientsession",
        "UpdateEntityFeature.RELEASE_NOTES",
    ):
        if required not in update_text:
            fail(f"update platform missing release-check route/text: {required}")

    if '"version": "0.1.16"' not in manifest_text:
        fail("manifest version was not bumped to 0.1.16")


def check_weather_renderer_options() -> None:
    const_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "const.py"
    flow_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "config_flow.py"
    init_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py"
    cards_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "renderer" / "cards.py"
    open_meteo_path = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "open_meteo.py"

    checks = {
        const_path: (
            'CONF_DISPLAY_MODE = "display_mode"',
            'DISPLAY_MODE_COLOUR = "colour"',
            'DISPLAY_MODE_MONO = "mono"',
            "DEFAULT_DISPLAY_MODE = DISPLAY_MODE_COLOUR",
        ),
        flow_path: (
            "CONF_DISPLAY_MODE",
            "vol.In([DISPLAY_MODE_COLOUR, DISPLAY_MODE_MONO])",
        ),
        init_path: (
            "display_mode = str(data.get(CONF_DISPLAY_MODE) or opts.get(CONF_DISPLAY_MODE, DEFAULT_DISPLAY_MODE))",
            "render_weather_card(card_data, colour_mode=display_mode)",
            'metadata["display_mode"] = display_mode',
            'PLATFORMS = ["sensor", "update", "button"]',
            "SERVICE_SYNC_WAKE_WINDOW",
            "hass.services.async_register(DOMAIN, SERVICE_SYNC_WAKE_WINDOW, handle_sync_wake_window)",
            "async_sync_wake_window",
            "_probe_existing_gateway",
        ),
        cards_path: (
            "COLOUR_MODE_COLOUR = \"colour\"",
            "COLOUR_MODE_MONO = \"mono\"",
            "GLYPHS: dict[str, tuple[str, ...]]",
            "_draw_bitmap_text",
            "_fit_bitmap_scale",
            "render_weather_card(data: WeatherCardData, colour_mode: str = COLOUR_MODE_COLOUR)",
            "_draw_bars(draw, data, colours)",
            "_draw_symbol(draw, kind, data, colours)",
        ),
        open_meteo_path: (
            "NOMINATIM_REVERSE_URL",
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


def main() -> None:
    check_branding()
    check_licenses()
    check_no_generated_cache_files()
    check_device_spec_alignment()
    check_update_platform()
    check_weather_renderer_options()
    check_sync_button()
    print("release guards passed")


if __name__ == "__main__":
    main()
