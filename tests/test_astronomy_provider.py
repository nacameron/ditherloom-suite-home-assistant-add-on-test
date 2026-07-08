import sys
import types
import builtins
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

ditherloom_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon")
ditherloom_package.__path__ = [str(ROOT / "custom_components" / "ditherloom_suite_ha_addon")]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon", ditherloom_package)

from custom_components.ditherloom_suite_ha_addon.astronomy_provider import (  # noqa: E402
    ASTRONOMY_ATTRIBUTION,
    ASTRONOMY_BODY_SIZE,
    ASTRONOMY_CONSTELLATION_NAME_SIZE,
    ASTRONOMY_FONT_SIZE_DELTA,
    ASTRONOMY_FOOTER_SIZE,
    ASTRONOMY_HEADING_SIZE,
    ASTRONOMY_LICENSE,
    ASTRONOMY_PROVIDER_IDS,
    ASTRONOMY_TITLE_SIZE,
    PROVIDER_ASTRONOMY_CONSTELLATION,
    render_astronomy_provider,
)
from custom_components.ditherloom_suite_ha_addon.renderer.palette import TEMPLATE_COLOURS  # noqa: E402


def test_astronomy_typography_is_bumped_two_points():
    assert ASTRONOMY_FONT_SIZE_DELTA == 2
    assert ASTRONOMY_HEADING_SIZE == 33
    assert ASTRONOMY_BODY_SIZE == 25
    assert ASTRONOMY_TITLE_SIZE == 27
    assert ASTRONOMY_CONSTELLATION_NAME_SIZE == 17
    assert ASTRONOMY_FOOTER_SIZE == 18


def test_astronomy_providers_render_panel_safe_cards(tmp_path: Path, monkeypatch):
    _force_skyfield_unavailable(monkeypatch)
    white = TEMPLATE_COLOURS["white"].rgb
    yellow = TEMPLATE_COLOURS["bright_yellow"].rgb

    for provider_id in ASTRONOMY_PROVIDER_IDS:
        artifact, card = render_astronomy_provider(
            provider_id,
            tmp_path / provider_id,
            provider_id,
            latitude=-33.8688,
            longitude=151.2093,
            location_name="Wollstonecraft",
            now=datetime(2026, 7, 7, 11, 0, tzinfo=timezone.utc),
        )

        assert card.image.size == (400, 300)
        assert artifact.metadata["attribution"] == ASTRONOMY_ATTRIBUTION
        assert artifact.metadata["license"] == ASTRONOMY_LICENSE
        assert "Skyfield and jplephem MIT libraries" in artifact.metadata["secondary_attribution"]
        assert "NASA/JPL DE421" in artifact.metadata["secondary_attribution"]
        assert "drawn in panel" not in artifact.metadata["astronomy_lines"]
        assert artifact.metadata["astronomy_skyfield_status"]
        assert (tmp_path / provider_id / f"{provider_id}.preview.png").exists()
        assert (tmp_path / provider_id / f"{provider_id}.source.png").exists()

        colours = {colour for _count, colour in card.image.convert("RGB").getcolors(maxcolors=1_000_000)}
        assert white in colours
        assert yellow in colours


def test_astronomy_constellation_uses_exact_white_lines_and_yellow_stars(tmp_path: Path, monkeypatch):
    _force_skyfield_unavailable(monkeypatch)
    white = TEMPLATE_COLOURS["white"].rgb
    yellow = TEMPLATE_COLOURS["bright_yellow"].rgb

    _artifact, card = render_astronomy_provider(
        PROVIDER_ASTRONOMY_CONSTELLATION,
        tmp_path,
        "constellation",
        latitude=-33.8688,
        longitude=151.2093,
        location_name="Wollstonecraft",
        now=datetime(2026, 7, 7, 11, 0, tzinfo=timezone.utc),
    )

    colours = {colour: count for count, colour in card.image.convert("RGB").getcolors(maxcolors=1_000_000)}
    assert colours[white] > 40
    assert colours[yellow] > 20
    assert card.lines[1].startswith("Bonus: ")
    assert "drawn in panel" not in card.lines
    with Image.open(tmp_path / "constellation.source.png") as image:
        assert image.size == (400, 300)


def _force_skyfield_unavailable(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "skyfield.api":
            raise ImportError("offline test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("offline test")))
