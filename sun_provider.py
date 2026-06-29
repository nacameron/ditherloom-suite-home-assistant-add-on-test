from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_provider_path = Path(__file__).resolve().parent / "custom_components" / "ditherloom_suite_ha_addon" / "sun_provider.py"
_spec = importlib.util.spec_from_file_location("_ditherloom_sun_provider", _provider_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load sun provider from {_provider_path}")
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

SunProviderData = _module.SunProviderData
build_sun_provider_data = _module.build_sun_provider_data

__all__ = ["SunProviderData", "build_sun_provider_data"]
