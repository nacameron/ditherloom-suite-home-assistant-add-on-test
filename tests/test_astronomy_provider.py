import sys
import types
import builtins
import json
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
    _bonus_constellation,
    _fetch_space_weather,
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


from custom_components.ditherloom_suite_ha_addon.astronomy_provider import _seasonal_constellation


def test_constellation_varies_across_render_cycles_for_southern_users():
    first = _seasonal_constellation(datetime(2026, 8, 21, 0, tzinfo=timezone.utc), -33.9)
    second = _seasonal_constellation(datetime(2026, 8, 21, 8, tzinfo=timezone.utc), -33.9)

    assert first != second


def test_bonus_constellation_varies_across_render_cycles_for_southern_users():
    pairs = {
        (
            _seasonal_constellation(when, -33.9),
            _bonus_constellation(_seasonal_constellation(when, -33.9), when, -33.9),
        )
        for when in (
            datetime(2026, 8, 21, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 21, 4, tzinfo=timezone.utc),
            datetime(2026, 8, 21, 8, tzinfo=timezone.utc),
            datetime(2026, 8, 21, 12, tzinfo=timezone.utc),
        )
    }

    assert len(pairs) >= 3
    assert all(primary != bonus for primary, bonus in pairs)


def test_noaa_dict_payload_populates_solar_activity(monkeypatch):
    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(url, timeout=10):
        url = str(url)
        if "noaa-planetary-k-index" in url:
            return Response(
                [
                    {"time_tag": "2026-08-21T00:00:00", "Kp": 2.0},
                    {"time_tag": "2026-08-21T03:00:00", "Kp": 4.33},
                ]
            )
        if "solar-wind-speed" in url:
            return Response([{"proton_speed": 491, "time_tag": "2026-08-21T07:35:00Z"}])
        if "ovation_aurora" in url:
            return Response({"coordinates": []})
        raise AssertionError(f"unexpected NOAA URL {url}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    result = _fetch_space_weather(-33.9, 151.2)

    assert result["kp_index"] == 4.3
    assert result["solar_activity"] == "Active solar wind"
    assert result["solar_wind_speed"] == 491
    assert result["space_weather_status"] == "NOAA/SWPC Kp"
