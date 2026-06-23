from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from functools import lru_cache
from datetime import datetime
from typing import Any, Dict

from .renderer.cards import WeatherCardData

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
REVERSE_GEOCODE_USER_AGENT = "Ditherloom-Suite-Home-Assistant-Add-On/0.1"

WEATHER_CODES = {
    0: "Sunny",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Cloudy",
    45: "Fog",
    48: "Fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy showers",
    95: "Thunderstorm",
    96: "Storm warning",
    99: "Storm warning",
}


def fetch_open_meteo_card(latitude: str, longitude: str, location: str) -> WeatherCardData:
    latitude, longitude = _normalise_coordinates(latitude, longitude)
    resolved_location = location.strip() or _reverse_location_name(latitude, longitude) or "Open-Meteo"
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
            ]
        ),
        "timezone": "auto",
        "forecast_days": "1",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }
    url = f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=12) as response:
        payload: Dict[str, Any] = json.loads(response.read().decode("utf-8"))

    current = payload.get("current", {})
    daily = payload.get("daily", {})
    code = int(current.get("weather_code", 0))
    condition = WEATHER_CODES.get(code, f"Code {code}")
    updated = current.get("time") or datetime.now().strftime("%H:%M")
    if "T" in updated:
        updated = updated.split("T", 1)[1]

    temp = _round_text(current.get("temperature_2m"))
    high = _round_text(_first(daily.get("temperature_2m_max")))
    low = _round_text(_first(daily.get("temperature_2m_min")))
    humidity = _percent(current.get("relative_humidity_2m"))
    uv = _round_text(_first(daily.get("uv_index_max")), digits=1)
    rain_probability = _percent(_first(daily.get("precipitation_probability_max")))
    wind = f"{_round_text(current.get('wind_speed_10m'))}km/h"
    feels = f"{_round_text(current.get('apparent_temperature'))}C"
    pressure = f"{_round_text(current.get('pressure_msl'))}hPa"

    details = (
        ("High", f"{high}C"),
        ("Low", f"{low}C"),
        ("Hum", humidity),
        ("UV", uv),
        ("Rain", rain_probability),
        ("Wind", wind),
    )
    alert = "Storm watch" if code in (95, 96, 99) else ""
    return WeatherCardData(
        location=resolved_location,
        condition=condition,
        temperature=temp,
        unit="C",
        high=high,
        low=low,
        rain=rain_probability,
        wind=wind,
        updated=updated,
        alert=alert,
        source_entity_id="open_meteo.direct",
        humidity=humidity,
        uv_index=uv,
        feels_like=feels,
        pressure=pressure,
        details=details,
    )


_COORDINATE_RE = re.compile(r"([+-]?\d+(?:\.\d+)?)")


def _normalise_coordinates(latitude: Any, longitude: Any) -> tuple[str, str]:
    if _coordinate_direction(latitude) in ("E", "W") and _coordinate_direction(longitude) in ("N", "S"):
        latitude, longitude = longitude, latitude

    return _normalise_coordinate(latitude, "latitude"), _normalise_coordinate(longitude, "longitude")


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
