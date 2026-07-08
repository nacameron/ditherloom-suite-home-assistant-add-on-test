import sys
import types
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

ditherloom_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon")
ditherloom_package.__path__ = [str(ROOT / "custom_components" / "ditherloom_suite_ha_addon")]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon", ditherloom_package)

from custom_components.ditherloom_suite_ha_addon.renderer.cards import (
    ForecastDayData,
    WeatherRadarData,
    WeatherHourlyData,
    WeatherHourlyPoint,
    WeatherForecastData,
    RADAR_PALETTES,
    _precip_background_name,
    render_weather_radar_card,
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
    assert TEMPLATE_COLOURS["white"].rgb in split_colours
    assert TEMPLATE_COLOURS["bright_yellow"].rgb in split_colours
    assert TEMPLATE_COLOURS["red"].rgb in seven_colours
    assert (255, 255, 255) not in seven_colours


def test_precipitation_background_uses_amount_not_probability_for_intensity():
    drizzle = WeatherHourlyData(
        blocks=(
            WeatherHourlyPoint(label="AM", precipitation_mm=0.1, precipitation_probability=95),
            WeatherHourlyPoint(label="PM", precipitation_mm=0.0, precipitation_probability=80),
        )
    )
    assert _precip_background_name(drizzle) == "precip_light"

    medium = WeatherHourlyData(
        blocks=(
            WeatherHourlyPoint(label="AM", precipitation_mm=2.0, precipitation_probability=40),
            WeatherHourlyPoint(label="PM", precipitation_mm=0.5, precipitation_probability=30),
        )
    )
    assert _precip_background_name(medium) == "precip_medium"

    heavy = WeatherHourlyData(
        blocks=(
            WeatherHourlyPoint(label="AM", precipitation_mm=6.0, precipitation_probability=45),
            WeatherHourlyPoint(label="PM", precipitation_mm=1.0, precipitation_probability=25),
        )
    )
    assert _precip_background_name(heavy) == "precip_heavy"


def test_weather_radar_palettes_render_with_visible_scale():
    basemap_colour = (137, 142, 128, 255)
    radar = Image.new("RGBA", (80, 80), basemap_colour)
    draw = ImageDraw.Draw(radar)
    draw.rectangle((8, 8, 30, 72), fill=(0, 210, 45, 180))
    draw.rectangle((30, 8, 52, 72), fill=(245, 180, 30, 210))
    draw.rectangle((52, 8, 74, 72), fill=(220, 40, 40, 230))
    payload = BytesIO()
    radar.save(payload, format="PNG")

    for palette in RADAR_PALETTES:
        image = render_weather_radar_card(
            WeatherRadarData(
                location="Wollstonecraft",
                radar_image=payload.getvalue(),
                attribution="OpenWeather",
                palette=palette,
            )
        )
        colours = {colour for _count, colour in image.convert("RGB").getcolors(maxcolors=1_000_000)}
        expected_scale_colours = {TEMPLATE_COLOURS[colour_name].rgb for _label, colour_name in RADAR_PALETTES[palette][1]}
        assert image.size == (400, 300)
        assert expected_scale_colours & colours
        assert TEMPLATE_COLOURS["black"].rgb in colours
        assert basemap_colour[:3] in colours
