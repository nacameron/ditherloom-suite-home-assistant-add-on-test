from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class SunProviderData:
    location: str
    date_label: str
    scene_id: str
    scene_name: str
    sunrise: str
    sunset: str
    civil_dawn: str
    civil_dusk: str
    day_length: str
    golden_morning: str
    golden_evening: str
    source_entity_id: str = "ditherloom.sunrise_sunset"
    attribution: str = "Sun times calculated locally from configured Home Assistant location."


def build_sun_provider_data(
    latitude: str,
    longitude: str,
    location: str,
    timezone_name: str | None,
    target_date: date | None = None,
    current_datetime: datetime | None = None,
) -> SunProviderData:
    lat = _bounded_float(latitude, -90.0, 90.0, "latitude")
    lon = _bounded_float(longitude, -180.0, 180.0, "longitude")
    tz = _load_timezone(timezone_name)
    now = current_datetime.astimezone(tz) if current_datetime else datetime.now(tz)
    target = target_date or now.date()
    scene_time = now if target_date is None else datetime.combine(target, time(12), tzinfo=tz)

    astronomical_dawn = _solar_event(target, lat, lon, tz, 108.0, sunrise=True)
    astronomical_dusk = _solar_event(target, lat, lon, tz, 108.0, sunrise=False)
    sunrise = _solar_event(target, lat, lon, tz, 90.833, sunrise=True)
    sunset = _solar_event(target, lat, lon, tz, 90.833, sunrise=False)
    civil_dawn = _solar_event(target, lat, lon, tz, 96.0, sunrise=True)
    civil_dusk = _solar_event(target, lat, lon, tz, 96.0, sunrise=False)

    if sunrise and sunset and sunset > sunrise:
        day_length = _format_duration(sunset - sunrise)
        golden_morning = f"{_format_time(sunrise)}-{_format_time(sunrise + timedelta(hours=1))}"
        golden_evening = f"{_format_time(max(sunrise, sunset - timedelta(hours=1)))}-{_format_time(sunset)}"
    else:
        day_length = "Polar day" if _is_polar_day(target, lat, lon) else "Polar night"
        golden_morning = "--"
        golden_evening = "--"
    scene_id, scene_name = _choose_sun_scene(scene_time, astronomical_dawn, civil_dawn, sunrise, sunset, civil_dusk, astronomical_dusk)

    return SunProviderData(
        location=location.strip() or "Home",
        date_label=target.strftime("%d %b").upper(),
        scene_id=scene_id,
        scene_name=scene_name,
        sunrise=_format_time(sunrise),
        sunset=_format_time(sunset),
        civil_dawn=_format_time(civil_dawn),
        civil_dusk=_format_time(civil_dusk),
        day_length=day_length,
        golden_morning=golden_morning,
        golden_evening=golden_evening,
    )


def _choose_sun_scene(
    now: datetime,
    astronomical_dawn: datetime | None,
    civil_dawn: datetime | None,
    sunrise: datetime | None,
    sunset: datetime | None,
    civil_dusk: datetime | None,
    astronomical_dusk: datetime | None,
) -> tuple[str, str]:
    if not sunrise or not sunset:
        return ("daylight", "Daylight") if _is_between_known(now, civil_dawn, civil_dusk) else ("night", "Night")
    if astronomical_dawn and now < astronomical_dawn:
        return "night", "Night"
    if astronomical_dawn and civil_dawn and astronomical_dawn <= now < civil_dawn:
        return "astronomical_twilight", "Astronomical Twilight"
    if civil_dawn and now < sunrise:
        return "civil_dawn", "Civil Dawn"
    if sunrise <= now < sunrise + timedelta(minutes=45):
        return "sunrise", "Sunrise"
    if now < sunrise + timedelta(hours=2):
        return "golden_morning", "Golden Morning"
    if now < sunset - timedelta(hours=2):
        return "daylight", "Daylight"
    if now < sunset - timedelta(minutes=45):
        return "golden_evening", "Golden Evening"
    if now < sunset + timedelta(minutes=30):
        return "sunset", "Sunset"
    if civil_dusk and now < civil_dusk:
        return "civil_dusk", "Civil Dusk"
    if astronomical_dusk and now < astronomical_dusk:
        return "astronomical_twilight", "Astronomical Twilight"
    return "night", "Night"


def _is_between_known(value: datetime, start: datetime | None, end: datetime | None) -> bool:
    return start is not None and end is not None and start <= value < end


def _bounded_float(value: str, low: float, high: float, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Sunrise / Sunset {label} is not configured") from exc
    if parsed < low or parsed > high:
        raise ValueError(f"Sunrise / Sunset {label} must be between {low:g} and {high:g}")
    return parsed


def _load_timezone(timezone_name: str | None) -> tzinfo:
    try:
        return ZoneInfo(timezone_name or "UTC")
    except Exception:
        return timezone.utc


def _solar_event(target: date, latitude: float, longitude: float, tz: tzinfo, zenith: float, sunrise: bool) -> datetime | None:
    # NOAA-style sunrise equation. Accuracy is sufficient for an ambient e-ink card.
    day_of_year = target.timetuple().tm_yday
    lng_hour = longitude / 15.0
    approx = day_of_year + ((6.0 - lng_hour) / 24.0 if sunrise else (18.0 - lng_hour) / 24.0)
    mean_anomaly = (0.9856 * approx) - 3.289
    true_long = mean_anomaly + (1.916 * math.sin(math.radians(mean_anomaly))) + (0.020 * math.sin(math.radians(2 * mean_anomaly))) + 282.634
    true_long = true_long % 360.0
    right_ascension = math.degrees(math.atan(0.91764 * math.tan(math.radians(true_long)))) % 360.0
    l_quadrant = math.floor(true_long / 90.0) * 90.0
    ra_quadrant = math.floor(right_ascension / 90.0) * 90.0
    right_ascension = (right_ascension + l_quadrant - ra_quadrant) / 15.0
    sin_dec = 0.39782 * math.sin(math.radians(true_long))
    cos_dec = math.cos(math.asin(sin_dec))
    cos_hour = (math.cos(math.radians(zenith)) - (sin_dec * math.sin(math.radians(latitude)))) / (
        cos_dec * math.cos(math.radians(latitude))
    )
    if cos_hour > 1.0 or cos_hour < -1.0:
        return None
    hour_angle = 360.0 - math.degrees(math.acos(cos_hour)) if sunrise else math.degrees(math.acos(cos_hour))
    hour_angle /= 15.0
    local_mean = hour_angle + right_ascension - (0.06571 * approx) - 6.622
    utc_hour = (local_mean - lng_hour) % 24.0
    whole_hours = int(utc_hour)
    minutes_float = (utc_hour - whole_hours) * 60.0
    whole_minutes = int(minutes_float)
    seconds = int(round((minutes_float - whole_minutes) * 60.0))
    if seconds == 60:
        seconds = 0
        whole_minutes += 1
    if whole_minutes == 60:
        whole_minutes = 0
        whole_hours = (whole_hours + 1) % 24
    utc_dt = datetime.combine(target, time(whole_hours, whole_minutes, seconds), tzinfo=timezone.utc)
    return utc_dt.astimezone(tz)


def _format_time(value: datetime | None) -> str:
    if value is None:
        return "--"
    return value.strftime("%H:%M")


def _format_duration(value: timedelta) -> str:
    minutes = max(0, int(value.total_seconds() // 60))
    return f"{minutes // 60}h {minutes % 60:02d}m"


def _is_polar_day(target: date, latitude: float, longitude: float) -> bool:
    noon = _solar_event(target, latitude, longitude, timezone.utc, 90.833, sunrise=False)
    return noon is None and abs(latitude) > 66.0
