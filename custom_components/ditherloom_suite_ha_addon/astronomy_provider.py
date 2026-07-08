from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .renderer.pack import RenderArtifact, render_to_artifact, write_artifact
from .renderer.palette import TEMPLATE_COLOURS

WIDTH = 400
HEIGHT = 300
ASTRONOMY_ASSET_DIR = Path(__file__).resolve().parent / "assets" / "astronomy_art"
FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
FONT_REGULAR = FONT_DIR / "BarlowCondensed-Regular.otf"

ASTRONOMY_ATTRIBUTION = "Ditherloom Astronomy; planetary data by NASA/JPL via Skyfield"
ASTRONOMY_LICENSE = (
    "Ditherloom artwork/text; Skyfield and jplephem MIT; NASA/JPL ephemeris data retained under source terms; "
    "NOAA/SWPC space-weather data public-domain unless otherwise noted; Open-Meteo CC BY 4.0"
)
ASTRONOMY_SOURCE_URL = "local://ditherloom/astronomy"
ASTRONOMY_SKYFIELD_URL = "https://rhodesmill.org/skyfield/"
ASTRONOMY_EPHEMERIS_URL = "https://naif.jpl.nasa.gov/naif/data.html"
ASTRONOMY_NOAA_ATTRIBUTION = "Solar and aurora data by NOAA/SWPC"
ASTRONOMY_NOAA_URL = "https://www.swpc.noaa.gov/"
ASTRONOMY_NOAA_TERMS_URL = "https://www.weather.gov/disclaimer"
ASTRONOMY_OPEN_METEO_ATTRIBUTION = "Viewing conditions by Open-Meteo"
ASTRONOMY_OPEN_METEO_URL = "https://open-meteo.com/"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
NOAA_SOLAR_WIND_URL = "https://services.swpc.noaa.gov/products/solar-wind/plasma-1-day.json"
NOAA_AURORA_URL = "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"

PROVIDER_ASTRONOMY_VISIBLE_PLANETS = "astronomy_visible_planets"
PROVIDER_ASTRONOMY_MOON_WATCH = "astronomy_moon_watch"
PROVIDER_ASTRONOMY_CONSTELLATION = "astronomy_constellation"
PROVIDER_ASTRONOMY_TONIGHT_SKY = "astronomy_tonight_sky"
PROVIDER_ASTRONOMY_OVERHEAD = "astronomy_overhead"
PROVIDER_ASTRONOMY_CONDITIONS = "astronomy_conditions"
PROVIDER_ASTRONOMY_SOLAR_ACTIVITY = "astronomy_solar_activity"
PROVIDER_ASTRONOMY_AURORA_WATCH = "astronomy_aurora_watch"

ASTRONOMY_PROVIDER_NAMES = {
    PROVIDER_ASTRONOMY_VISIBLE_PLANETS: "Visible Planets",
    PROVIDER_ASTRONOMY_MOON_WATCH: "Moon Watch",
    PROVIDER_ASTRONOMY_CONSTELLATION: "Constellation Tonight",
    PROVIDER_ASTRONOMY_TONIGHT_SKY: "Tonight's Sky",
    PROVIDER_ASTRONOMY_OVERHEAD: "Planets Overhead",
    PROVIDER_ASTRONOMY_CONDITIONS: "Astronomy View Conditions",
    PROVIDER_ASTRONOMY_SOLAR_ACTIVITY: "Solar Activity",
    PROVIDER_ASTRONOMY_AURORA_WATCH: "Aurora Watch",
}

ASTRONOMY_BACKGROUND_NAMES = {
    PROVIDER_ASTRONOMY_VISIBLE_PLANETS: "astronomy_visible_planets",
    PROVIDER_ASTRONOMY_MOON_WATCH: "astronomy_moon_watch",
    PROVIDER_ASTRONOMY_CONSTELLATION: "astronomy_constellation",
    PROVIDER_ASTRONOMY_TONIGHT_SKY: "astronomy_tonight_sky",
    PROVIDER_ASTRONOMY_OVERHEAD: "astronomy_overhead",
    PROVIDER_ASTRONOMY_CONDITIONS: "astronomy_tonight_sky",
    PROVIDER_ASTRONOMY_SOLAR_ACTIVITY: "astronomy_visible_planets",
    PROVIDER_ASTRONOMY_AURORA_WATCH: "astronomy_overhead",
}

ASTRONOMY_PROVIDER_IDS = tuple(ASTRONOMY_PROVIDER_NAMES)
PROMOTED_HEADLINE_PROVIDERS = {
    PROVIDER_ASTRONOMY_VISIBLE_PLANETS,
    PROVIDER_ASTRONOMY_MOON_WATCH,
    PROVIDER_ASTRONOMY_TONIGHT_SKY,
}
FULLY_CENTERED_PROVIDERS = {
    PROVIDER_ASTRONOMY_CONDITIONS,
    PROVIDER_ASTRONOMY_SOLAR_ACTIVITY,
    PROVIDER_ASTRONOMY_AURORA_WATCH,
}
BODY_BOX = (82, 82, 318, 228)
SPACE_CONDITIONS_BODY_BOX = (58, 76, 342, 226)
CONSTELLATION_TEXT_BOX = (166, 86, 340, 232)
MAIN_CONSTELLATION_DRAW_BOX = (48, 90, 150, 164)
BONUS_CONSTELLATION_DRAW_BOX = (58, 184, 138, 224)
MAIN_CONSTELLATION_NAME_BOX = (42, 166, 154, 184)
BONUS_NAME_BOX = (42, 224, 154, 242)
TITLE_BOX = (68, 58, 332, 84)
FOOTER_BOX = (58, 238, 342, 260)
ASTRONOMY_FONT_SIZE_DELTA = 2
ASTRONOMY_HEADING_SIZE = 33
ASTRONOMY_HEADING_MIN_SIZE = 23
ASTRONOMY_BODY_SIZE = 25
ASTRONOMY_TITLE_SIZE = 27
ASTRONOMY_TITLE_MIN_SIZE = 17
ASTRONOMY_CONSTELLATION_NAME_SIZE = 17
ASTRONOMY_CONSTELLATION_NAME_MIN_SIZE = 11
ASTRONOMY_FOOTER_SIZE = 18
ASTRONOMY_FOOTER_MIN_SIZE = 12
ASTRONOMY_HEADING_GAP = 14
ASTRONOMY_HEADING_BOX_HEIGHT = 34
ASTRONOMY_BODY_LINE_HEIGHT = 28
ASTRONOMY_BODY_LINE_BOX_HEIGHT = 27
ASTRONOMY_PROMOTED_LINE_HEIGHT = 29


@dataclass(frozen=True)
class AstronomyCard:
    provider_id: str
    provider_name: str
    date_label: str
    skyfield_status: str
    headline: str
    lines: tuple[str, ...]
    image: Image.Image
    artifact: RenderArtifact


def render_astronomy_provider(
    provider_id: str,
    output_dir: Path,
    stem: str,
    *,
    latitude: float,
    longitude: float,
    location_name: str,
    now: datetime | None = None,
) -> tuple[RenderArtifact, AstronomyCard]:
    if provider_id not in ASTRONOMY_PROVIDER_IDS:
        raise ValueError(f"Unsupported Astronomy provider: {provider_id}")
    now = now or datetime.now(timezone.utc)
    local_now = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    context = _astronomy_context(
        local_now,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        cache_dir=output_dir / "ephemeris",
    )
    image, headline, lines = render_astronomy_card(provider_id, context)
    content_key = f"{provider_id}_{context['date']}"
    artifact = render_to_artifact(image, content_key, [ASTRONOMY_SOURCE_URL])
    artifact.metadata.update(_metadata_for(provider_id, context, headline, lines))
    write_artifact(artifact, output_dir, stem)
    image.save(output_dir / f"{stem}.source.png")
    return artifact, AstronomyCard(
        provider_id=provider_id,
        provider_name=ASTRONOMY_PROVIDER_NAMES[provider_id],
        date_label=str(context["date_label"]),
        skyfield_status=str(context["skyfield_status"]),
        headline=headline,
        lines=tuple(lines),
        image=image,
        artifact=artifact,
    )


def render_astronomy_card(provider_id: str, context: dict[str, Any]) -> tuple[Image.Image, str, tuple[str, ...]]:
    image = _load_background(ASTRONOMY_BACKGROUND_NAMES[provider_id]).copy()
    _attach_protected_mask(image)
    draw = ImageDraw.Draw(image)
    yellow = TEMPLATE_COLOURS["bright_yellow"].rgb
    white = TEMPLATE_COLOURS["white"].rgb
    provider_name = ASTRONOMY_PROVIDER_NAMES[provider_id]
    headline, lines = _copy_for_provider(provider_id, context)

    if provider_id == PROVIDER_ASTRONOMY_CONSTELLATION:
        constellation = str(context.get("constellation") or "Southern Cross")
        bonus = _bonus_constellation(constellation)
        orientation = float(context.get("constellation_orientation_degrees", 0.0) or 0.0)
        _draw_constellation(image, constellation, MAIN_CONSTELLATION_DRAW_BOX, orientation_degrees=orientation, line_width=2, star_radius=5)
        _draw_constellation(image, bonus, BONUS_CONSTELLATION_DRAW_BOX, orientation_degrees=orientation * 0.5, line_width=1, star_radius=3)
        _draw_single_centered(
            image,
            MAIN_CONSTELLATION_NAME_BOX,
            constellation.upper(),
            ASTRONOMY_CONSTELLATION_NAME_SIZE,
            white,
            ASTRONOMY_CONSTELLATION_NAME_MIN_SIZE,
        )
        _draw_single_centered(
            image,
            BONUS_NAME_BOX,
            bonus.upper(),
            ASTRONOMY_CONSTELLATION_NAME_SIZE,
            white,
            ASTRONOMY_CONSTELLATION_NAME_MIN_SIZE,
        )
        _draw_centered_text(image, CONSTELLATION_TEXT_BOX, headline.upper(), lines, yellow, white)
    elif provider_id in PROMOTED_HEADLINE_PROVIDERS:
        _draw_single_centered(image, TITLE_BOX, headline.upper(), ASTRONOMY_TITLE_SIZE, yellow, ASTRONOMY_TITLE_MIN_SIZE)
        _draw_centered_lines(image, BODY_BOX, lines, white)
    elif provider_id in FULLY_CENTERED_PROVIDERS:
        _draw_centered_text(image, SPACE_CONDITIONS_BODY_BOX, headline.upper(), lines, yellow, white)
    else:
        _draw_centered_text(image, BODY_BOX, headline.upper(), lines, yellow, white)
    if (
        provider_id not in PROMOTED_HEADLINE_PROVIDERS
        and provider_id not in FULLY_CENTERED_PROVIDERS
        and headline.strip().lower() != provider_name.strip().lower()
    ):
        _draw_single_centered(image, TITLE_BOX, provider_name.upper(), ASTRONOMY_TITLE_SIZE, yellow, ASTRONOMY_TITLE_MIN_SIZE)
    _draw_single_centered(
        image,
        FOOTER_BOX,
        _footer_for_provider(provider_id, context).upper(),
        ASTRONOMY_FOOTER_SIZE,
        white,
        ASTRONOMY_FOOTER_MIN_SIZE,
    )
    return image, headline, tuple(lines)


def _load_background(name: str) -> Image.Image:
    path = ASTRONOMY_ASSET_DIR / f"{name}.png"
    if not path.exists():
        raise FileNotFoundError(f"Astronomy artwork missing: {name}")
    image = Image.open(path).convert("RGB")
    if image.size != (WIDTH, HEIGHT):
        image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    return image


def _attach_protected_mask(image: Image.Image) -> Image.Image:
    image.info["ditherloom_protected_mask"] = Image.new("L", image.size, 0)
    return image


def _astronomy_context(
    now: datetime,
    *,
    latitude: float,
    longitude: float,
    location_name: str,
    cache_dir: Path,
) -> dict[str, Any]:
    day = now.date()
    evening = datetime.combine(day, time(21, 0), tzinfo=now.tzinfo or timezone.utc)
    context = _fallback_context(evening, latitude, longitude, location_name, "fallback: not loaded")
    try:
        from skyfield.api import Loader, wgs84

        cache_dir.mkdir(parents=True, exist_ok=True)
        loader = Loader(str(cache_dir))
        timescale = loader.timescale()
        eph = loader("de421.bsp")
        utc_evening = evening.astimezone(timezone.utc)
        t = timescale.utc(
            utc_evening.year,
            utc_evening.month,
            utc_evening.day,
            utc_evening.hour,
            utc_evening.minute,
        )
        earth = eph["earth"]
        observer = earth + wgs84.latlon(latitude, longitude)
        body_keys = {
            "Moon": "moon",
            "Mercury": "mercury",
            "Venus": "venus",
            "Mars": "mars",
            "Jupiter": "jupiter barycenter",
            "Saturn": "saturn barycenter",
        }
        altitudes: dict[str, float] = {}
        azimuths: dict[str, float] = {}
        for label, key in body_keys.items():
            apparent = observer.at(t).observe(eph[key]).apparent()
            alt, az, _distance = apparent.altaz()
            altitudes[label] = round(float(alt.degrees), 1)
            azimuths[label] = round(float(az.degrees), 1)
        sun_alt = float(observer.at(t).observe(eph["sun"]).apparent().altaz()[0].degrees)
        longitudes: dict[str, float] = {}
        for label, key in {"Sun": "sun", "Moon": "moon"}.items():
            _lat, lon, _distance = earth.at(t).observe(eph[key]).apparent().ecliptic_latlon()
            longitudes[label] = float(lon.degrees % 360)
        moon_angle = (longitudes["Moon"] - longitudes["Sun"]) % 360
        visible = [
            name
            for name in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")
            if altitudes.get(name, -90.0) >= 5.0 and sun_alt <= -6.0
        ]
        overhead = max(altitudes, key=lambda name: altitudes[name])
        context.update(
            {
                "skyfield_status": "skyfield_de421",
                "ephemeris": "JPL DE421 via Skyfield",
                "visible_planets": visible,
                "altitudes": altitudes,
                "azimuths": azimuths,
                "moon_phase": _moon_phase_from_angle(moon_angle),
                "moon_altitude": altitudes.get("Moon", 0.0),
                "moon_azimuth": azimuths.get("Moon", 0.0),
                "overhead_body": overhead,
                "overhead_altitude": altitudes[overhead],
                "sun_altitude": round(sun_alt, 1),
            }
        )
    except Exception as err:
        context["skyfield_status"] = f"fallback: {type(err).__name__}"
    context["constellation"] = _seasonal_constellation(day, latitude)
    context["constellation_orientation_degrees"] = _constellation_orientation_degrees(day, latitude, longitude)
    context.update(_fetch_viewing_conditions(day, latitude, longitude))
    context.update(_fetch_space_weather(latitude, longitude))
    context["footer"] = f"{_date_label(day)} | Ditherloom"
    return context


def _fallback_context(
    when: datetime,
    latitude: float,
    longitude: float,
    location_name: str,
    status: str,
) -> dict[str, Any]:
    day = when.date()
    seed = int(hashlib.sha256(f"{day.isoformat()}:{latitude:.2f}:{longitude:.2f}".encode("utf-8")).hexdigest()[:4], 16)
    planet_sets = (
        ("Venus", "Mars"),
        ("Jupiter", "Saturn"),
        ("Mercury", "Venus"),
        ("Mars", "Jupiter"),
    )
    visible = list(planet_sets[seed % len(planet_sets)])
    return {
        "date": day.isoformat(),
        "date_label": _date_label(day),
        "location_name": location_name or "Home",
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "skyfield_status": status,
        "ephemeris": "fallback seasonal astronomy guide",
        "visible_planets": visible,
        "altitudes": {name: 15.0 + index * 10 for index, name in enumerate(("Moon", *visible))},
        "azimuths": {name: 110.0 + index * 40 for index, name in enumerate(("Moon", *visible))},
        "moon_phase": _moon_phase_name(day),
        "moon_altitude": 28.0,
        "moon_azimuth": 120.0,
        "overhead_body": visible[0],
        "overhead_altitude": 54.0,
        "sun_altitude": -12.0,
        "constellation": _seasonal_constellation(day, latitude),
        "constellation_orientation_degrees": _constellation_orientation_degrees(day, latitude, longitude),
        "cloud_cover": "--",
        "visibility_km": "--",
        "viewing_condition": "Check cloud cover",
        "viewing_advice": "Cloud data unavailable",
        "kp_index": "--",
        "solar_wind_speed": "--",
        "solar_activity": "Space weather quiet",
        "aurora_probability": "--",
        "aurora_direction": "poleward horizon",
        "aurora_visibility": "unlikely naked-eye",
        "space_weather_status": status,
        "footer": f"{_date_label(day)} | Ditherloom",
    }


def _fetch_viewing_conditions(day: date, latitude: float, longitude: float) -> dict[str, Any]:
    params = {
        "latitude": f"{latitude:.6f}",
        "longitude": f"{longitude:.6f}",
        "hourly": "cloud_cover,visibility",
        "timezone": "auto",
        "forecast_days": "1",
    }
    try:
        url = f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        hourly = payload.get("hourly", {})
        cloud_values = [_float(value, 0.0) for value in list(hourly.get("cloud_cover") or [])]
        visibility_values = [_float(value, 0.0) for value in list(hourly.get("visibility") or [])]
        night_slice = cloud_values[18:24] or cloud_values
        visibility_slice = visibility_values[18:24] or visibility_values
        cloud = round(sum(night_slice) / max(1, len(night_slice)))
        visibility_km = round((sum(visibility_slice) / max(1, len(visibility_slice))) / 1000, 1) if visibility_slice else "--"
        if cloud <= 25:
            condition = "Clear viewing"
            advice = "Good naked-eye sky"
        elif cloud <= 55:
            condition = "Patchy cloud"
            advice = "Breaks may reveal planets"
        elif cloud <= 80:
            condition = "Cloud may obscure"
            advice = "Best with patience"
        else:
            condition = "Mostly obscured"
            advice = "Viewing likely poor"
        return {
            "cloud_cover": cloud,
            "visibility_km": visibility_km,
            "viewing_condition": condition,
            "viewing_advice": advice,
            "viewing_source": "Open-Meteo",
        }
    except Exception as err:
        return {
            "cloud_cover": "--",
            "visibility_km": "--",
            "viewing_condition": "Cloud unknown",
            "viewing_advice": "Open-Meteo unavailable",
            "viewing_source": f"fallback: {type(err).__name__}",
        }


def _fetch_space_weather(latitude: float, longitude: float) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kp_index": "--",
        "solar_wind_speed": "--",
        "solar_activity": "Solar data pending",
        "aurora_probability": "--",
        "aurora_direction": _aurora_direction(latitude),
        "aurora_visibility": "unlikely naked-eye",
        "space_weather_status": "fallback: not loaded",
    }
    try:
        with urllib.request.urlopen(NOAA_KP_URL, timeout=10) as response:
            kp_rows = json.loads(response.read().decode("utf-8"))
        kp = _latest_noaa_value(kp_rows, 1)
        result["kp_index"] = "--" if kp is None else round(kp, 1)
        result["solar_activity"] = _solar_activity_label(kp)
        result["aurora_visibility"] = _aurora_visibility_label(kp, latitude)
        result["space_weather_status"] = "NOAA/SWPC Kp"
    except Exception as err:
        result["space_weather_status"] = f"fallback: kp {type(err).__name__}"
    try:
        with urllib.request.urlopen(NOAA_SOLAR_WIND_URL, timeout=10) as response:
            wind_rows = json.loads(response.read().decode("utf-8"))
        speed = _latest_noaa_value(wind_rows, 1)
        if speed is not None:
            result["solar_wind_speed"] = int(round(speed))
    except Exception:
        pass
    try:
        result["aurora_probability"] = _fetch_aurora_probability(latitude, longitude)
    except Exception:
        pass
    return result


def _latest_noaa_value(rows: Any, value_index: int) -> float | None:
    if not isinstance(rows, list):
        return None
    for row in reversed(rows[1:] if rows and isinstance(rows[0], list) else rows):
        if not isinstance(row, list) or len(row) <= value_index:
            continue
        try:
            return float(row[value_index])
        except (TypeError, ValueError):
            continue
    return None


def _fetch_aurora_probability(latitude: float, longitude: float) -> str:
    with urllib.request.urlopen(NOAA_AURORA_URL, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    coordinates = payload.get("coordinates") or []
    if not coordinates:
        return "--"
    best = None
    best_distance = float("inf")
    target_lon = ((longitude + 180) % 360) - 180
    for item in coordinates:
        if not isinstance(item, list) or len(item) < 3:
            continue
        lon = ((float(item[0]) + 180) % 360) - 180
        lat = float(item[1])
        value = float(item[2])
        distance = abs(lat - latitude) + abs(lon - target_lon) * max(0.2, math.cos(math.radians(latitude)))
        if distance < best_distance:
            best_distance = distance
            best = value
    return "--" if best is None else f"{int(round(best))}%"


def _solar_activity_label(kp: float | None) -> str:
    if kp is None:
        return "Solar data pending"
    if kp >= 7:
        return "Strong storm watch"
    if kp >= 5:
        return "Geomagnetic storm"
    if kp >= 4:
        return "Active solar wind"
    return "Quiet space weather"


def _aurora_visibility_label(kp: float | None, latitude: float) -> str:
    abs_lat = abs(latitude)
    if kp is None:
        return "check later"
    if abs_lat >= 60 and kp >= 3:
        return "possible naked-eye"
    if abs_lat >= 50 and kp >= 5:
        return "possible naked-eye"
    if abs_lat >= 40 and kp >= 7:
        return "low horizon chance"
    return "unlikely naked-eye"


def _aurora_direction(latitude: float) -> str:
    return "south" if latitude < 0 else "north"


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _copy_for_provider(provider_id: str, context: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    location = str(context.get("location_name") or "Home")
    if provider_id == PROVIDER_ASTRONOMY_VISIBLE_PLANETS:
        visible = list(context.get("visible_planets") or [])
        if not visible:
            return "Planet Watch", ("No bright planets", "clearly placed", "after dusk")
        return "Planet Watch", (", ".join(visible[:3]), "best after dusk", location)
    if provider_id == PROVIDER_ASTRONOMY_MOON_WATCH:
        return "Moon Watch", (
            str(context.get("moon_phase") or "Moon phase"),
            f"Alt {context.get('moon_altitude', '--')} deg",
            location,
        )
    if provider_id == PROVIDER_ASTRONOMY_CONSTELLATION:
        constellation = str(context.get("constellation") or "Tonight")
        return "Look For", (constellation, f"Bonus: {_bonus_constellation(constellation)}", location)
    if provider_id == PROVIDER_ASTRONOMY_TONIGHT_SKY:
        visible = list(context.get("visible_planets") or [])
        planet_line = "Planets: " + (", ".join(visible[:2]) if visible else "quiet sky")
        return "Tonight's Sky", (str(context.get("moon_phase") or "Moon"), planet_line, location)
    if provider_id == PROVIDER_ASTRONOMY_OVERHEAD:
        body = str(context.get("overhead_body") or "Moon")
        altitude = context.get("overhead_altitude", "--")
        return "Highest Body", (body, f"{altitude} deg high", location)
    if provider_id == PROVIDER_ASTRONOMY_CONDITIONS:
        cloud = context.get("cloud_cover", "--")
        visibility = context.get("visibility_km", "--")
        return "Astronomy View Conditions", (
            str(context.get("viewing_condition") or "Cloud unknown"),
            f"Cloud {cloud}%",
            f"Visibility {visibility} km",
            str(context.get("viewing_advice") or location),
        )
    if provider_id == PROVIDER_ASTRONOMY_SOLAR_ACTIVITY:
        wind = context.get("solar_wind_speed", "--")
        kp = context.get("kp_index", "--")
        viewing = str(context.get("viewing_condition") or "Cloud unknown")
        return "Solar Activity", (
            str(context.get("solar_activity") or "Space weather"),
            f"Kp {kp}",
            f"Wind {wind} km/s",
            f"Viewing {viewing}",
        )
    if provider_id == PROVIDER_ASTRONOMY_AURORA_WATCH:
        probability = context.get("aurora_probability", "--")
        viewing = str(context.get("viewing_condition") or "Cloud unknown")
        return "Aurora Watch", (
            str(context.get("aurora_visibility") or "check later"),
            f"Chance {probability}",
            f"Face {context.get('aurora_direction', 'poleward')}",
            f"Viewing {viewing}",
        )
    return "Astronomy", ("Sky guide", location)


def _metadata_for(provider_id: str, context: dict[str, Any], headline: str, lines: tuple[str, ...]) -> dict[str, Any]:
    provider_name = ASTRONOMY_PROVIDER_NAMES[provider_id]
    return {
        "provider_id": provider_id,
        "provider_name": provider_name,
        "source": "ditherloom_local_astronomy",
        "source_name": ASTRONOMY_ATTRIBUTION,
        "source_url": ASTRONOMY_SOURCE_URL,
        "attribution": ASTRONOMY_ATTRIBUTION,
        "attribution_url": ASTRONOMY_SOURCE_URL,
        "license": ASTRONOMY_LICENSE,
        "license_url": ASTRONOMY_SOURCE_URL,
        "secondary_attribution": "Skyfield and jplephem MIT libraries; NASA/JPL DE421 ephemeris data",
        "secondary_attribution_url": ASTRONOMY_EPHEMERIS_URL,
        "secondary_license": "Skyfield MIT; jplephem MIT; NASA/JPL ephemeris data retained under source terms; NOAA/SWPC public-domain unless otherwise noted; Open-Meteo CC BY 4.0",
        "secondary_license_url": ASTRONOMY_SKYFIELD_URL,
        "noaa_swpc_attribution": ASTRONOMY_NOAA_ATTRIBUTION,
        "noaa_swpc_url": ASTRONOMY_NOAA_URL,
        "noaa_terms_url": ASTRONOMY_NOAA_TERMS_URL,
        "open_meteo_attribution": ASTRONOMY_OPEN_METEO_ATTRIBUTION,
        "open_meteo_url": ASTRONOMY_OPEN_METEO_URL,
        "astronomy_date": context.get("date"),
        "astronomy_date_label": context.get("date_label"),
        "astronomy_location_name": context.get("location_name"),
        "astronomy_latitude": context.get("latitude"),
        "astronomy_longitude": context.get("longitude"),
        "astronomy_skyfield_status": context.get("skyfield_status"),
        "astronomy_ephemeris": context.get("ephemeris"),
        "astronomy_visible_planets": context.get("visible_planets"),
        "astronomy_altitudes": context.get("altitudes"),
        "astronomy_azimuths": context.get("azimuths"),
        "astronomy_moon_phase": context.get("moon_phase"),
        "astronomy_constellation": context.get("constellation"),
        "astronomy_constellation_orientation_degrees": context.get("constellation_orientation_degrees"),
        "astronomy_overhead_body": context.get("overhead_body"),
        "astronomy_cloud_cover": context.get("cloud_cover"),
        "astronomy_visibility_km": context.get("visibility_km"),
        "astronomy_viewing_condition": context.get("viewing_condition"),
        "astronomy_kp_index": context.get("kp_index"),
        "astronomy_solar_wind_speed": context.get("solar_wind_speed"),
        "astronomy_aurora_probability": context.get("aurora_probability"),
        "astronomy_aurora_direction": context.get("aurora_direction"),
        "astronomy_aurora_visibility": context.get("aurora_visibility"),
        "astronomy_space_weather_status": context.get("space_weather_status"),
        "astronomy_headline": headline,
        "astronomy_lines": list(lines),
        "data_transformations": (
            "Local Ditherloom Astronomy V1. Sky text is generated from Ditherloom-owned "
            "rules and Skyfield/JPL ephemeris positions when available. Supplied 400x300 "
            "Ditherloom astronomy backgrounds are kept as RGB artwork; text, constellation "
            "lines, and stars are pasted as exact panel-safe white/yellow pixels after the "
            "background pass so they remain crisp in the hybrid renderer."
        ),
    }


def _draw_centered_text(
    image: Image.Image,
    box: tuple[int, int, int, int],
    heading: str,
    lines: tuple[str, ...],
    heading_fill: tuple[int, int, int],
    body_fill: tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = box
    draw = ImageDraw.Draw(image)
    heading_font = _font_that_fits(heading, x2 - x1 - 8, ASTRONOMY_HEADING_SIZE, ASTRONOMY_HEADING_MIN_SIZE)
    body_font = _font(ASTRONOMY_BODY_SIZE)
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(_wrap_to_width(str(line), body_font, x2 - x1 - 10))
    if len(wrapped) > 4:
        wrapped = wrapped[:4]
    total_h = _text_height(heading_font, heading) + ASTRONOMY_HEADING_GAP + len(wrapped) * ASTRONOMY_BODY_LINE_HEIGHT
    y = y1 + max(0, (y2 - y1 - total_h) // 2)
    _draw_single_centered_with_font(image, (x1, y, x2, y + ASTRONOMY_HEADING_BOX_HEIGHT), heading, heading_font, heading_fill)
    y += _text_height(heading_font, heading) + ASTRONOMY_HEADING_GAP
    for line in wrapped:
        _draw_single_centered_with_font(image, (x1, y, x2, y + ASTRONOMY_BODY_LINE_BOX_HEIGHT), line, body_font, body_fill)
        y += ASTRONOMY_BODY_LINE_HEIGHT


def _draw_centered_lines(
    image: Image.Image,
    box: tuple[int, int, int, int],
    lines: tuple[str, ...],
    body_fill: tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = box
    body_font = _font(ASTRONOMY_BODY_SIZE)
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(_wrap_to_width(str(line), body_font, x2 - x1 - 10))
    if len(wrapped) > 5:
        wrapped = wrapped[:5]
    total_h = len(wrapped) * ASTRONOMY_PROMOTED_LINE_HEIGHT
    y = y1 + max(0, (y2 - y1 - total_h) // 2)
    for line in wrapped:
        _draw_single_centered_with_font(image, (x1, y, x2, y + ASTRONOMY_BODY_LINE_BOX_HEIGHT), line, body_font, body_fill)
        y += ASTRONOMY_PROMOTED_LINE_HEIGHT


def _draw_single_centered(
    image: Image.Image,
    box: tuple[int, int, int, int],
    text: str,
    size: int,
    fill: tuple[int, int, int],
    minimum: int,
) -> None:
    font = _font_that_fits(text, box[2] - box[0] - 6, size, minimum)
    _draw_single_centered_with_font(image, box, text, font, fill)


def _draw_single_centered_with_font(
    image: Image.Image,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    left, top, right, bottom = font.getbbox(str(text))
    width = right - left
    height = bottom - top
    x = box[0] + (box[2] - box[0] - width) / 2 - left
    y = box[1] + (box[3] - box[1] - height) / 2 - top
    _draw_crisp_text(image, (int(x), int(y)), str(text), font, fill)


def _draw_crisp_text(
    image: Image.Image,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    mask = Image.new("1", image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text(xy, text, font=font, fill=1)
    image.paste(fill, mask=mask)
    protected = image.info.get("ditherloom_protected_mask")
    if isinstance(protected, Image.Image):
        protected.paste(255, mask=mask)


def _draw_constellation(
    image: Image.Image,
    name: str,
    box: tuple[int, int, int, int],
    *,
    orientation_degrees: float = 0.0,
    line_width: int = 2,
    star_radius: int = 4,
) -> None:
    draw = ImageDraw.Draw(image)
    x1, y1, x2, y2 = box
    points = _constellation_points(name)
    mapped = _oriented_points(points, box, orientation_degrees)
    white = TEMPLATE_COLOURS["white"].rgb
    yellow = TEMPLATE_COLOURS["bright_yellow"].rgb
    protected = image.info.get("ditherloom_protected_mask")
    mask_draw = ImageDraw.Draw(protected) if isinstance(protected, Image.Image) else None
    for start, end in zip(mapped, mapped[1:]):
        draw.line((*start, *end), fill=white, width=line_width)
        if mask_draw is not None:
            mask_draw.line((*start, *end), fill=255, width=line_width)
    for x, y in mapped:
        _draw_luxe_star(draw, mask_draw, x, y, star_radius, yellow, white)


def _oriented_points(
    points: tuple[tuple[float, float], ...],
    box: tuple[int, int, int, int],
    orientation_degrees: float,
) -> list[tuple[int, int]]:
    x1, y1, x2, y2 = box
    radians = math.radians(orientation_degrees)
    sin_a = math.sin(radians)
    cos_a = math.cos(radians)
    mapped: list[tuple[int, int]] = []
    for px, py in points:
        dx = px - 0.5
        dy = py - 0.5
        rx = dx * cos_a - dy * sin_a
        ry = dx * sin_a + dy * cos_a
        mapped.append((x1 + int((rx + 0.5) * (x2 - x1)), y1 + int((ry + 0.5) * (y2 - y1))))
    return mapped


def _draw_luxe_star(
    draw: ImageDraw.ImageDraw,
    mask_draw: ImageDraw.ImageDraw | None,
    x: int,
    y: int,
    radius: int,
    fill: tuple[int, int, int],
    centre: tuple[int, int, int],
) -> None:
    points = (
        (x, y - radius),
        (x + max(1, radius // 3), y - max(1, radius // 3)),
        (x + radius, y),
        (x + max(1, radius // 3), y + max(1, radius // 3)),
        (x, y + radius),
        (x - max(1, radius // 3), y + max(1, radius // 3)),
        (x - radius, y),
        (x - max(1, radius // 3), y - max(1, radius // 3)),
    )
    draw.polygon(points, fill=fill)
    draw.point((x, y), fill=centre)
    if mask_draw is not None:
        mask_draw.polygon(points, fill=255)
        mask_draw.point((x, y), fill=255)


def _bonus_constellation(primary: str) -> str:
    normalized = primary.lower()
    for candidate in ("Orion", "Scorpius", "Cygnus", "Southern Cross"):
        if candidate.lower() not in normalized:
            return candidate
    return "Orion"


def _constellation_points(name: str) -> tuple[tuple[float, float], ...]:
    normalized = name.lower()
    if "cross" in normalized:
        return ((0.52, 0.05), (0.47, 0.34), (0.52, 0.62), (0.56, 0.94), (0.52, 0.62), (0.17, 0.46), (0.52, 0.62), (0.88, 0.48))
    if "scorpius" in normalized:
        return ((0.08, 0.15), (0.24, 0.22), (0.42, 0.28), (0.58, 0.42), (0.66, 0.62), (0.56, 0.80), (0.36, 0.88), (0.22, 0.76))
    if "orion" in normalized:
        return ((0.18, 0.20), (0.42, 0.40), (0.50, 0.50), (0.58, 0.60), (0.82, 0.80), (0.58, 0.60), (0.76, 0.26), (0.42, 0.40), (0.22, 0.74))
    return ((0.12, 0.74), (0.30, 0.35), (0.48, 0.26), (0.70, 0.45), (0.86, 0.22))


def _seasonal_constellation(day: date, latitude: float) -> str:
    month = day.month
    southern = latitude < 0
    if southern:
        if month in {3, 4, 5, 6, 7, 8}:
            return "Southern Cross"
        if month in {6, 7, 8, 9}:
            return "Scorpius"
        return "Orion"
    if month in {11, 12, 1, 2, 3}:
        return "Orion"
    if month in {6, 7, 8}:
        return "Scorpius"
    return "Cygnus"


def _constellation_orientation_degrees(day: date, latitude: float, longitude: float) -> float:
    # Compact locale-aware orientation for the 400x300 guide card. It follows
    # hemisphere, season, and longitude so the drawing is not a fixed icon.
    seasonal = (day.timetuple().tm_yday / 365.2425) * 360.0
    longitude_term = longitude * 0.5
    hemisphere_term = 180.0 if latitude < 0 else 0.0
    return (seasonal + longitude_term + hemisphere_term) % 360.0


def _footer_for_provider(provider_id: str, context: dict[str, Any]) -> str:
    if provider_id == PROVIDER_ASTRONOMY_CONDITIONS:
        return f"{context['date_label']} | Open-Meteo | Ditherloom"
    if provider_id in {PROVIDER_ASTRONOMY_SOLAR_ACTIVITY, PROVIDER_ASTRONOMY_AURORA_WATCH}:
        return f"{context['date_label']} | NOAA/SWPC | Ditherloom"
    return f"{context['date_label']} | Skyfield/JPL | Ditherloom"


def _date_label(day: date) -> str:
    suffix = "th"
    if day.day % 100 not in (11, 12, 13):
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day.day % 10, "th")
    return f"{day.day}{suffix} {day.strftime('%b')}"


def _moon_phase_name(day: date) -> str:
    known_new = date(2000, 1, 6)
    age = ((day - known_new).days % 29.53058867)
    if age < 1.84566:
        return "New Moon"
    if age < 5.53699:
        return "Waxing Crescent"
    if age < 9.22831:
        return "First Quarter"
    if age < 12.91963:
        return "Waxing Gibbous"
    if age < 16.61096:
        return "Full Moon"
    if age < 20.30228:
        return "Waning Gibbous"
    if age < 23.99361:
        return "Last Quarter"
    if age < 27.68493:
        return "Waning Crescent"
    return "New Moon"


def _moon_phase_from_angle(angle: float) -> str:
    if angle < 22.5 or angle >= 337.5:
        return "New Moon"
    if angle < 67.5:
        return "Waxing Crescent"
    if angle < 112.5:
        return "First Quarter"
    if angle < 157.5:
        return "Waxing Gibbous"
    if angle < 202.5:
        return "Full Moon"
    if angle < 247.5:
        return "Waning Gibbous"
    if angle < 292.5:
        return "Last Quarter"
    return "Waning Crescent"


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_REGULAR), size)
    except OSError:
        return ImageFont.load_default()


def _font_that_fits(text: str, width: int, start: int, minimum: int) -> ImageFont.ImageFont:
    for size in range(start, minimum - 1, -1):
        font = _font(size)
        left, top, right, bottom = font.getbbox(text)
        if right - left <= width and bottom - top <= 32:
            return font
    return _font(minimum)


def _wrap_to_width(text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if font.getlength(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _text_height(font: ImageFont.ImageFont, text: str) -> int:
    top = font.getbbox(text)[1]
    bottom = font.getbbox(text)[3]
    return bottom - top
