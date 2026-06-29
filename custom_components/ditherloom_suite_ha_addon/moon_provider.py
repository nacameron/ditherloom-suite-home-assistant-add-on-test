from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo


SYNODIC_MONTH_DAYS = 29.530588853
KNOWN_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)


@dataclass(frozen=True)
class MoonProviderData:
    location: str
    date_label: str
    phase_name: str
    illumination: str
    moon_age: str
    moonrise: str
    moonset: str
    next_full: str
    next_new: str
    primary_label: str
    primary_value: str
    secondary_prefix: str
    secondary_value: str
    source_entity_id: str = "ditherloom.moon_phase"
    attribution: str = "Moon phase calculated locally from configured Home Assistant location."


def build_moon_provider_data(
    latitude: str,
    longitude: str,
    location: str,
    timezone_name: str | None,
    target_date: date | None = None,
    current_datetime: datetime | None = None,
) -> MoonProviderData:
    lat = _bounded_float(latitude, -90.0, 90.0, "latitude")
    lon = _bounded_float(longitude, -180.0, 180.0, "longitude")
    tz = _load_timezone(timezone_name)
    now = current_datetime.astimezone(tz) if current_datetime else datetime.now(tz)
    target = target_date or now.date()
    local_noon = datetime.combine(target, time(12, 0), tzinfo=tz)
    age = _moon_age_days(local_noon.astimezone(timezone.utc))
    phase_fraction = age / SYNODIC_MONTH_DAYS
    illumination = int(round(((1.0 - math.cos(2.0 * math.pi * phase_fraction)) / 2.0) * 100.0))
    phase_name = _phase_name(age)
    moonrise = _approx_moonrise(target, tz, age)
    moonset = moonrise + timedelta(hours=12, minutes=25)
    primary_label, primary_value, secondary_prefix, secondary_value = _next_moon_event_display(now, target, tz, age)

    return MoonProviderData(
        location=location.strip() or "Home",
        date_label=target.strftime("%d %b").upper(),
        phase_name=phase_name,
        illumination=f"{illumination}%",
        moon_age=f"{age:.1f}d",
        moonrise=_format_time(moonrise),
        moonset=_format_time(moonset),
        next_full=_format_date(_next_phase_date(local_noon, age, SYNODIC_MONTH_DAYS / 2.0)),
        next_new=_format_date(_next_phase_date(local_noon, age, SYNODIC_MONTH_DAYS)),
        primary_label=primary_label,
        primary_value=primary_value,
        secondary_prefix=secondary_prefix,
        secondary_value=secondary_value,
    )


def _moon_age_days(moment_utc: datetime) -> float:
    elapsed_days = (moment_utc - KNOWN_NEW_MOON).total_seconds() / 86400.0
    return elapsed_days % SYNODIC_MONTH_DAYS


def _phase_name(age: float) -> str:
    if age < 1.85 or age >= 27.68:
        return "New Moon"
    if age < 5.54:
        return "Waxing Crescent"
    if age < 9.23:
        return "First Quarter"
    if age < 12.92:
        return "Waxing Gibbous"
    if age < 16.61:
        return "Full Moon"
    if age < 20.30:
        return "Waning Gibbous"
    if age < 23.99:
        return "Last Quarter"
    return "Waning Crescent"


def _approx_moonrise(target: date, tz: tzinfo, age: float) -> datetime:
    # Ambient approximation: moonrise drifts about 50 minutes later each day.
    rise_minutes = int(round((6 * 60) + (age * 50.47)))
    day_offset, minute_of_day = divmod(rise_minutes, 24 * 60)
    hour, minute = divmod(minute_of_day, 60)
    return datetime.combine(target + timedelta(days=day_offset), time(hour, minute), tzinfo=tz)


def _next_phase_date(local_noon: datetime, age: float, target_age: float) -> date:
    days_until = (target_age - age) % SYNODIC_MONTH_DAYS
    if days_until < 0.25:
        days_until += SYNODIC_MONTH_DAYS
    return (local_noon + timedelta(days=days_until)).date()


def _bounded_float(value: str, low: float, high: float, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Moon Phase {label} is not configured") from exc
    if parsed < low or parsed > high:
        raise ValueError(f"Moon Phase {label} must be between {low:g} and {high:g}")
    return parsed


def _load_timezone(timezone_name: str | None) -> tzinfo:
    try:
        return ZoneInfo(timezone_name or "UTC")
    except Exception:
        return timezone.utc


def _format_time(value: datetime) -> str:
    return value.strftime("%H:%M")


def _format_date(value: date) -> str:
    return value.strftime("%d %b").upper()


def _next_moon_event_display(now: datetime, target: date, tz: tzinfo, age: float) -> tuple[str, str, str, str]:
    events: list[tuple[str, datetime, str, datetime]] = []
    for offset in range(0, 3):
        event_date = target + timedelta(days=offset)
        event_age = (age + offset) % SYNODIC_MONTH_DAYS
        rise = _approx_moonrise(event_date, tz, event_age)
        moonset = rise + timedelta(hours=12, minutes=25)
        if rise >= now:
            events.append(("MOONRISE", rise, "sets", moonset))
        if moonset >= now:
            events.append(("MOONSET", moonset, "rose", rise))
    if not events:
        rise = _approx_moonrise(target + timedelta(days=1), tz, (age + 1) % SYNODIC_MONTH_DAYS)
        return "MOONRISE", _format_time(rise), "sets", _format_time(rise + timedelta(hours=12, minutes=25))
    label, event_time, secondary_prefix, secondary_time = min(events, key=lambda item: item[1])
    return label, _format_time(event_time), secondary_prefix, _format_time(secondary_time)
