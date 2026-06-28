from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_provider_path = Path(__file__).resolve().parent / "custom_components" / "ditherloom_suite_ha_addon" / "moon_provider.py"
_spec = importlib.util.spec_from_file_location("_ditherloom_moon_provider", _provider_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load moon provider from {_provider_path}")
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

MoonProviderData = _module.MoonProviderData
build_moon_provider_data = _module.build_moon_provider_data

__all__ = ["MoonProviderData", "build_moon_provider_data"]
