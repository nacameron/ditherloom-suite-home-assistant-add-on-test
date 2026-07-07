from datetime import datetime
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ditherloom_suite_ha_addon"

custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

component_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon")
component_package.__path__ = [str(COMPONENT)]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon", component_package)

from custom_components.ditherloom_suite_ha_addon.astrology_provider import (
    ASTROLOGY_PROVIDER_ID,
    normalize_signs,
    render_astrology_provider,
    selected_sign_for_time,
)


def test_astrology_provider_renders_panel_card_with_attribution(tmp_path):
    artifact, card = render_astrology_provider(
        tmp_path,
        "astrology-test",
        signs=["libra", "pisces"],
        interval_minutes=60,
        now=datetime(2026, 7, 5, 12, 0, 0),
    )

    assert card.image.size == (400, 300)
    assert artifact.metadata["provider_id"] == ASTROLOGY_PROVIDER_ID
    assert artifact.metadata["provider_name"] == "Daily Astrology"
    assert "Skyfield" in artifact.metadata["attribution"]
    assert "NASA/JPL" in artifact.metadata["license"]
    assert "secondary_attribution" in artifact.metadata
    assert artifact.metadata["astrology_sign"] in {"libra", "pisces"}
    assert artifact.metadata["astrology_moon_phase"]
    assert artifact.metadata["astrology_skyfield_status"] == "skyfield_de421"
    assert artifact.metadata["astrology_body"]
    assert (tmp_path / "astrology-test.preview.png").exists()
    assert (tmp_path / "astrology-test.ppbin").exists()

    colours = {colour for _count, colour in card.image.convert("RGB").getcolors(maxcolors=1_000_000)}
    assert (0, 0, 0) in colours
    assert (135, 30, 34) in colours


def test_astrology_sign_selection_rotates_selected_signs_only():
    when = datetime(2026, 7, 5, 12, 0, 0)

    assert normalize_signs(["bad", "taurus", "aries"]) == ["aries", "taurus"]
    assert normalize_signs(["pisces", "capricorn", "gemini"]) == ["gemini", "capricorn", "pisces"]
    assert selected_sign_for_time(["aries", "cancer"], when, 60) in {"aries", "cancer"}
    assert selected_sign_for_time([], when, 60) == "aries"
