from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
_custom_components = types.ModuleType("custom_components")
_custom_components.__path__ = [str(_root / "custom_components")]
sys.modules.setdefault("custom_components", _custom_components)
_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon")
_package.__path__ = [str(_root / "custom_components" / "ditherloom_suite_ha_addon")]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon", _package)
_renderer_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon.renderer")
_renderer_package.__path__ = [str(_root / "custom_components" / "ditherloom_suite_ha_addon" / "renderer")]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon.renderer", _renderer_package)

_module_name = "custom_components.ditherloom_suite_ha_addon.renderer.cards"
_module_path = _root / "custom_components" / "ditherloom_suite_ha_addon" / "renderer" / "cards.py"
_spec = importlib.util.spec_from_file_location(_module_name, _module_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load renderer cards from {_module_path}")
_module = importlib.util.module_from_spec(_spec)
sys.modules[_module_name] = _module
_spec.loader.exec_module(_module)

WeatherCardData = _module.WeatherCardData
SunCardData = _module.SunCardData
MoonCardData = _module.MoonCardData
render_weather_card = _module.render_weather_card
render_modern_weather_card = _module.render_modern_weather_card
render_sun_card = _module.render_sun_card
render_moon_card = _module.render_moon_card

__all__ = [
    "WeatherCardData",
    "SunCardData",
    "MoonCardData",
    "render_weather_card",
    "render_modern_weather_card",
    "render_sun_card",
    "render_moon_card",
]
