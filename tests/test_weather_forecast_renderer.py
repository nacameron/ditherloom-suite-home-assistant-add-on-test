import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

ditherloom_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon")
ditherloom_package.__path__ = [str(ROOT / "custom_components" / "ditherloom_suite_ha_addon")]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon", ditherloom_package)

from custom_components.ditherloom_suite_ha_addon.renderer.cards import (
    ForecastDayData,
    WeatherForecastData,
    render_seven_day_weather_card,
    render_today_tomorrow_weather_card,
)
from custom_components.ditherloom_suite_ha_addon.renderer.palette import TEMPLATE_COLOURS


def test_forecast_weather_cards_render_panel_safe_text_colours():
    forecast = WeatherForecastData(
        location="Moorabbin",
        days=tuple(
            ForecastDayData(date_label=label, condition=condition, high=str(24 + index), low=str(13 + index), unit="C")
            for index, (label, condition) in enumerate(
                (
                    ("6 Jul", "Sunny"),
                    ("7 Jul", "Rain"),
                    ("8 Jul", "Partly cloudy"),
                    ("9 Jul", "Cloudy"),
                    ("10 Jul", "Storm"),
                    ("11 Jul", "Fog"),
                    ("12 Jul", "Snow"),
                )
            )
        ),
    )

    split = render_today_tomorrow_weather_card(forecast)
    seven = render_seven_day_weather_card(forecast)

    assert split.size == (400, 300)
    assert seven.size == (400, 300)
    split_colours = {colour for _count, colour in split.convert("RGB").getcolors(maxcolors=1_000_000)}
    seven_colours = {colour for _count, colour in seven.convert("RGB").getcolors(maxcolors=1_000_000)}
    assert TEMPLATE_COLOURS["red"].rgb in split_colours
    assert TEMPLATE_COLOURS["yellow"].rgb in split_colours
    assert TEMPLATE_COLOURS["red"].rgb in seven_colours
