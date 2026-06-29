from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ditherloom_suite_ha_addon"
INIT = COMPONENT / "__init__.py"
BUTTON = COMPONENT / "button.py"


def test_home_assistant_brand_assets_are_packaged():
    for name in ("icon.png", "logo.png", "brand/icon.png", "brand/logo.png"):
        path = COMPONENT / name
        assert path.exists()
        assert path.stat().st_size > 0


def test_sync_wifi_button_is_not_created_and_stale_entity_is_removed():
    button_source = BUTTON.read_text(encoding="utf-8")
    init_source = INIT.read_text(encoding="utf-8")

    assert "Synchronise Wi-Fi wake window" not in button_source
    assert "Synchronise Wi-Fi wake window" not in init_source
    assert "STALE_FRONTEND_ENTITY_NAMES" in init_source
    assert "sync_wifi_wake_window" in init_source
    assert "registry.async_remove(entity_entry.entity_id)" in init_source
