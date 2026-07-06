from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from functools import lru_cache
from datetime import datetime
from typing import Any, Dict

from .renderer.cards import ForecastDayData, WeatherCardData, WeatherForecastData

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
REVERSE_GEOCODE_USER_AGENT = "Ditherloom-Suite-Home-Assistant-Add-On/0.1"

WEATHER_CODES = {
    0: "Sunny",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Cloudy",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Heavy thunderstorm with hail",
}

NIGHT_AWARE_CODES = {0, 1, 2}
OPEN_METEO_ATTRIBUTION = "Weather data by Open-Meteo.com."
OPEN_METEO_ATTRIBUTION_URL = "https://open-meteo.com/"
OPEN_METEO_LICENSE = "CC BY 4.0"
OPEN_METEO_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
OPEN_METEO_CHANGES = "Weather values are rounded and rendered into a Ditherloom e-ink card."
NOMINATIM_ATTRIBUTION = "Place-name lookup by OpenStreetMap contributors via Nominatim."
NOMINATIM_ATTRIBUTION_URL = "https://www.openstreetmap.org/copyright"
NOMINATIM_LICENSE = "ODbL"
NOMINATIM_LICENSE_URL = "https://opendatacommons.org/licenses/odbl/"


def fetch_open_meteo_card(
    latitude: str,
    longitude: str,
    location: str,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
) -> WeatherCardData:
    latitude, longitude = _normalise_coordinates(latitude, longitude)
    resolved_location = location.strip() or _reverse_location_name(latitude, longitude) or "Open-Meteo"
    temperature_unit = _temperature_unit(temperature_unit)
    wind_speed_unit = _wind_speed_unit(wind_speed_unit)
    temperature_suffix = "F" if temperature_unit == "fahrenheit" else "C"
    wind_suffix = "mph" if wind_speed_unit == "mph" else "km/h"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "weather_code",
                "cloud_cover",
                "is_day",
                "pressure_msl",
                "wind_speed_10m",
                "wind_gusts_10m",
            ]
        ),
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "uv_index_max",
                "precipitation_probability_max",
                "precipitation_sum",
                "rain_sum",
                "showers_sum",
                "snowfall_sum",
                "wind_gusts_10m_max",
            ]
        ),
        "timezone": "auto",
        "forecast_days": "1",
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,
        "precipitation_unit": "mm",
    }
    url = f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=12) as response:
        payload: Dict[str, Any] = json.loads(response.read().decode("utf-8"))

    current = payload.get("current", {})
    daily = payload.get("daily", {})
    code = int(current.get("weather_code", 0))
    condition = _condition_text(code, current.get("is_day"))
    updated = current.get("time") or datetime.now().strftime("%H:%M")
    if "T" in updated:
        updated = updated.split("T", 1)[1]

    temp = _round_text(current.get("temperature_2m"))
    high = _round_text(_first(daily.get("temperature_2m_max")))
    low = _round_text(_first(daily.get("temperature_2m_min")))
    humidity = _percent(current.get("relative_humidity_2m"))
    uv = _round_text(_first(daily.get("uv_index_max")), digits=1)
    rain_probability = _percent(_first(daily.get("precipitation_probability_max")))
    wind = f"{_round_text(current.get('wind_speed_10m'))}{wind_suffix}"
    feels = f"{_round_text(current.get('apparent_temperature'))}{temperature_suffix}"
    pressure = f"{_round_text(current.get('pressure_msl'))}hPa"
    alert = _derived_alert(
        code=code,
        temperature=current.get("temperature_2m"),
        apparent_temperature=current.get("apparent_temperature"),
        humidity=current.get("relative_humidity_2m"),
        precipitation=current.get("precipitation"),
        daily_precipitation=_first(daily.get("precipitation_sum")),
        rain_sum=_first(daily.get("rain_sum")),
        showers_sum=_first(daily.get("showers_sum")),
        snowfall_sum=_first(daily.get("snowfall_sum")),
        wind_speed=current.get("wind_speed_10m"),
        wind_gust=current.get("wind_gusts_10m"),
        daily_wind_gust=_first(daily.get("wind_gusts_10m_max")),
        uv_index=_first(daily.get("uv_index_max")),
        rain_probability=_first(daily.get("precipitation_probability_max")),
        temperature_unit=temperature_unit,
        wind_speed_unit=wind_speed_unit,
    )

    details = (
        ("High", f"{high}{temperature_suffix}"),
        ("Low", f"{low}{temperature_suffix}"),
        ("Hum", humidity),
        ("UV", uv),
        ("Rain", rain_probability),
        ("Wind", wind),
    )
    return WeatherCardData(
        location=resolved_location,
        condition=condition,
        temperature=temp,
        unit=temperature_suffix,
        high=high,
        low=low,
        rain=rain_probability,
        wind=wind,
        updated=updated,
        alert=alert,
        source_entity_id="open_meteo.direct",
        attribution=f"{OPEN_METEO_ATTRIBUTION} {NOMINATIM_ATTRIBUTION if not location.strip() else ''}".strip(),
        humidity=humidity,
        uv_index=uv,
        feels_like=feels,
        pressure=pressure,
        details=details,
    )


def fetch_open_meteo_forecast(
    latitude: str,
    longitude: str,
    location: str,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
    days: int = 7,
) -> WeatherForecastData:
    latitude, longitude = _normalise_coordinates(latitude, longitude)
    resolved_location = location.strip() or _reverse_location_name(latitude, longitude) or "Open-Meteo"
    temperature_unit = _temperature_unit(temperature_unit)
    wind_speed_unit = _wind_speed_unit(wind_speed_unit)
    temperature_suffix = "F" if temperature_unit == "fahrenheit" else "C"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(["temperature_2m", "weather_code", "is_day"]),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
            ]
        ),
        "timezone": "auto",
        "forecast_days": str(max(2, min(7, int(days)))),
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,
        "precipitation_unit": "mm",
    }
    url = f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=12) as response:
        payload: Dict[str, Any] = json.loads(response.read().decode("utf-8"))

    current = payload.get("current", {})
    daily = payload.get("daily", {})
    times = list(daily.get("time") or [])
    codes = list(daily.get("weather_code") or [])
    highs = list(daily.get("temperature_2m_max") or [])
    lows = list(daily.get("temperature_2m_min") or [])
    rain = list(daily.get("precipitation_probability_max") or [])
    forecast_days: list[ForecastDayData] = []
    for index, date_value in enumerate(times[:7]):
        code = _list_item(codes, index, 0)
        forecast_days.append(
            ForecastDayData(
                date_label=_date_label(date_value),
                condition=_condition_text(int(code or 0), 1),
                high=_round_text(_list_item(highs, index)),
                low=_round_text(_list_item(lows, index)),
                rain=_percent(_list_item(rain, index)),
                unit=temperature_suffix,
            )
        )
    while len(forecast_days) < 7:
        forecast_days.append(
            ForecastDayData(
                date_label="--",
                condition="Weather",
                high="--",
                low="--",
                rain="--",
                unit=temperature_suffix,
            )
        )
    updated = current.get("time") or datetime.now().strftime("%H:%M")
    if "T" in updated:
        updated = updated.split("T", 1)[1]
    return WeatherForecastData(
        location=resolved_location,
        days=tuple(forecast_days[:7]),
        updated=updated,
        source_entity_id="open_meteo.direct",
        attribution=f"{OPEN_METEO_ATTRIBUTION} {NOMINATIM_ATTRIBUTION if not location.strip() else ''}".strip(),
    )


_COORDINATE_RE = re.compile(r"([+-]?\d+(?:\.\d+)?)")


def _normalise_coordinates(latitude: Any, longitude: Any) -> tuple[str, str]:
    if _coordinate_direction(latitude) in ("E", "W") and _coordinate_direction(longitude) in ("N", "S"):
        latitude, longitude = longitude, latitude

    return _normalise_coordinate(latitude, "latitude"), _normalise_coordinate(longitude, "longitude")


def _temperature_unit(value: Any) -> str:
    return "fahrenheit" if str(value).strip().lower() in {"fahrenheit", "f", "imperial"} else "celsius"


def _wind_speed_unit(value: Any) -> str:
    return "mph" if str(value).strip().lower() in {"mph", "m/h", "imperial"} else "kmh"


def _coordinate_direction(value: Any) -> str | None:
    upper = str(value or "").strip().upper()
    for candidate in ("N", "S", "E", "W"):
        if re.search(rf"(^|[^A-Z]){candidate}([^A-Z]|$)", upper):
            return candidate
    return None


def _normalise_coordinate(value: Any, axis: str) -> str:
    raw = str(value or "").strip()
    match = _COORDINATE_RE.search(raw)
    if not match:
        raise ValueError(f"{axis} must contain a numeric coordinate")

    number = float(match.group(1))
    upper = raw.upper()
    direction = _coordinate_direction(upper)

    if direction in ("S", "W"):
        number = -abs(number)
    elif direction in ("N", "E"):
        number = abs(number)

    limit = 90 if axis == "latitude" else 180
    if not -limit <= number <= limit:
        raise ValueError(f"{axis} must be between {-limit} and {limit}")

    return f"{number:.6f}".rstrip("0").rstrip(".")


@lru_cache(maxsize=64)
def _reverse_location_name(latitude: str, longitude: str) -> str:
    params = {
        "format": "jsonv2",
        "lat": latitude,
        "lon": longitude,
        "zoom": "10",
        "addressdetails": "1",
    }
    url = f"{NOMINATIM_REVERSE_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": REVERSE_GEOCODE_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload: Dict[str, Any] = json.loads(response.read().decode("utf-8"))
    except Exception:
        return ""

    address = payload.get("address")
    if not isinstance(address, dict):
        return _display_name_fallback(payload)
    for key in ("suburb", "city_district", "town", "city", "village", "municipality", "county", "state"):
        value = address.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return _display_name_fallback(payload)


def _display_name_fallback(payload: Dict[str, Any]) -> str:
    display_name = payload.get("display_name")
    if not isinstance(display_name, str):
        return ""
    first = display_name.split(",", 1)[0].strip()
    return first[:32]


def _first(value: Any) -> Any:
    if isinstance(value, list) and value:
        return value[0]
    return value


def _list_item(values: list[Any], index: int, default: Any = None) -> Any:
    return values[index] if index < len(values) else default


def _date_label(value: Any) -> str:
    try:
        parsed = datetime.fromisoformat(str(value)).date()
    except ValueError:
        return str(value or "--")[:6]
    return parsed.strftime("%d %b").lstrip("0")


def _round_text(value: Any, digits: int = 0) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "--"
    if digits == 0:
        return str(int(round(number)))
    return f"{number:.{digits}f}"


def _percent(value: Any) -> str:
    rounded = _round_text(value)
    if rounded == "--":
        return "--"
    return f"{rounded}%"


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _temperature_celsius(value: Any, temperature_unit: str) -> float | None:
    number = _float_or_none(value)
    if number is None:
        return None
    if temperature_unit == "fahrenheit":
        return (number - 32.0) * 5.0 / 9.0
    return number


def _wind_kmh(value: Any, wind_speed_unit: str) -> float | None:
    number = _float_or_none(value)
    if number is None:
        return None
    if wind_speed_unit == "mph":
        return number * 1.609344
    return number


def _max_present(*values: float | None) -> float | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _derived_alert(
    *,
    code: int,
    temperature: Any,
    apparent_temperature: Any,
    humidity: Any,
    precipitation: Any,
    daily_precipitation: Any,
    rain_sum: Any,
    showers_sum: Any,
    snowfall_sum: Any,
    wind_speed: Any,
    wind_gust: Any,
    daily_wind_gust: Any,
    uv_index: Any,
    rain_probability: Any,
    temperature_unit: str,
    wind_speed_unit: str,
) -> str:
    temp_c = _temperature_celsius(temperature, temperature_unit)
    apparent_c = _temperature_celsius(apparent_temperature, temperature_unit)
    effective_temp_c = _max_present(temp_c, apparent_c)
    humidity_percent = _float_or_none(humidity)
    current_precip_mm = _float_or_none(precipitation)
    daily_precip_mm = _max_present(
        _float_or_none(daily_precipitation),
        _float_or_none(rain_sum),
        _float_or_none(showers_sum),
    )
    snowfall_cm = _float_or_none(snowfall_sum)
    wind_kmh = _wind_kmh(wind_speed, wind_speed_unit)
    gust_kmh = _max_present(
        _wind_kmh(wind_gust, wind_speed_unit),
        _wind_kmh(daily_wind_gust, wind_speed_unit),
        wind_kmh,
    )
    uv = _float_or_none(uv_index)
    rain_chance = _float_or_none(rain_probability)

    if code in (96, 99):
        return "Hail storm"
    if code in (95,):
        return "Thunderstorm"
    if code in (85, 86, 71, 73, 75, 77) or (snowfall_cm is not None and snowfall_cm >= 5.0):
        return "Snow"
    if code in (65, 67, 82) or (current_precip_mm is not None and current_precip_mm >= 10.0) or (
        daily_precip_mm is not None and daily_precip_mm >= 50.0
    ):
        return "Heavy rain"
    if (
        effective_temp_c is not None
        and effective_temp_c >= 35.0
        and humidity_percent is not None
        and humidity_percent <= 25.0
        and gust_kmh is not None
        and gust_kmh >= 40.0
        and (rain_chance is None or rain_chance <= 25.0)
    ):
        return "Bushfire risk"
    if (apparent_c is not None and apparent_c >= 38.0) or (temp_c is not None and temp_c >= 40.0) or (
        uv is not None and uv >= 11.0 and effective_temp_c is not None and effective_temp_c >= 32.0
    ):
        return "Extreme heat"
    if (apparent_c is not None and apparent_c <= -10.0) or (temp_c is not None and temp_c <= -5.0):
        return "Extreme cold"
    if gust_kmh is not None and gust_kmh >= 63.0:
        return "High wind"
    return ""


def _condition_text(code: int, is_day: Any) -> str:
    if code in NIGHT_AWARE_CODES and str(is_day) == "0":
        if code == 2:
            return "Partly cloudy night"
        return "Clear night"
    return WEATHER_CODES.get(code, f"Code {code}")
