from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .renderer.pack import RenderArtifact, render_to_artifact, write_artifact
from .renderer.palette import TEMPLATE_COLOURS

WIDTH = 400
HEIGHT = 300
ASTROLOGY_ASSET_DIR = Path(__file__).resolve().parent / "assets" / "astrology_art"
ASTROLOGY_ATTRIBUTION = "Ditherloom Astrology; planetary data by NASA/JPL via Skyfield"
ASTROLOGY_LICENSE = "Ditherloom artwork/text; Skyfield and jplephem MIT; NASA/JPL ephemeris data retained under source terms"
ASTROLOGY_PROVIDER_ID = "daily_astrology"
ASTROLOGY_PROVIDER_NAME = "Daily Astrology"
ASTROLOGY_SOURCE_URL = "local://ditherloom/astrology"
ASTROLOGY_SKYFIELD_URL = "https://rhodesmill.org/skyfield/"
ASTROLOGY_JPLEPHEM_URL = "https://github.com/brandon-rhodes/python-jplephem"
ASTROLOGY_EPHEMERIS_URL = "https://naif.jpl.nasa.gov/naif/data.html"
TEXT_BOX = (56, 96, 344, 214)
TITLE_BOX = (92, 56, 166, 74)
DATE_BOX = (234, 56, 308, 74)
MOON_PHASE_BOX = (72, 248, 184, 264)
FOOTER_BOX = (216, 248, 328, 264)
BODY_MAX_LINES = 5

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
FONT_REGULAR = FONT_DIR / "BarlowCondensed-Regular.otf"
FONT_BODY = FONT_DIR / "Kalam-Regular.ttf"

SIGN_ORDER = (
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
)

SIGN_NAMES = {
    "aries": "Aries",
    "taurus": "Taurus",
    "gemini": "Gemini",
    "cancer": "Cancer",
    "leo": "Leo",
    "virgo": "Virgo",
    "libra": "Libra",
    "scorpio": "Scorpio",
    "sagittarius": "Sagittarius",
    "capricorn": "Capricorn",
    "aquarius": "Aquarius",
    "pisces": "Pisces",
}

SIGN_PROFILES = {
    "aries": ("fire", "cardinal", "initiative"),
    "taurus": ("earth", "fixed", "steadiness"),
    "gemini": ("air", "mutable", "conversation"),
    "cancer": ("water", "cardinal", "care"),
    "leo": ("fire", "fixed", "confidence"),
    "virgo": ("earth", "mutable", "craft"),
    "libra": ("air", "cardinal", "balance"),
    "scorpio": ("water", "fixed", "focus"),
    "sagittarius": ("fire", "mutable", "range"),
    "capricorn": ("earth", "cardinal", "structure"),
    "aquarius": ("air", "fixed", "perspective"),
    "pisces": ("water", "mutable", "imagination"),
}

ELEMENT_LINES = {
    "fire": (
        "Move first, then refine the plan.",
        "Choose the brave action that still leaves room to listen.",
        "Let momentum carry one clean decision.",
    ),
    "earth": (
        "Put care into the practical thing in front of you.",
        "A simple routine gives the day its anchor.",
        "Small repairs create more progress than big promises.",
    ),
    "air": (
        "A clear message changes the shape of the day.",
        "Ask the better question before choosing a side.",
        "Make space for one useful conversation.",
    ),
    "water": (
        "Trust the signal under the noise.",
        "Care is strongest when it has a clear boundary.",
        "Let feeling guide you, then let rhythm steady you.",
    ),
}

MODE_LINES = {
    "cardinal": (
        "Start with the smallest useful step.",
        "Lead gently, but do lead.",
        "Set the tone before the day sets it for you.",
    ),
    "fixed": (
        "Hold the line where it matters.",
        "Keep what is working and improve one edge.",
        "Your steadiness is the useful force today.",
    ),
    "mutable": (
        "Stay flexible without scattering your attention.",
        "Adapt the route, not the destination.",
        "A small change of wording opens the path.",
    ),
}

FOCUS_LINES = {
    "initiative": (
        "Say yes to the task that wakes you up.",
        "Put your energy where a first move matters.",
        "Begin before the moment becomes over-managed.",
        "One bold start will teach you what to adjust.",
    ),
    "steadiness": (
        "Protect the pace that keeps you well.",
        "Choose the dependable answer over the loud one.",
        "Let patience turn effort into something lasting.",
        "Keep the promise that makes the day feel grounded.",
    ),
    "conversation": (
        "Let one honest exchange do the heavy lifting.",
        "Name the idea while it is still fresh.",
        "A lighter question may open a better doorway.",
        "Listen for the detail hiding inside casual words.",
    ),
    "care": (
        "Offer warmth without carrying everything.",
        "Make room for tenderness and a firm boundary.",
        "Protect the place where your feelings can settle.",
        "Let support be simple, direct, and sustainable.",
    ),
    "confidence": (
        "Be visible in one place that matters.",
        "Let your warmth lead without demanding the stage.",
        "Choose the gesture that makes courage feel natural.",
        "Stand behind the thing you know is yours.",
    ),
    "craft": (
        "Polish the detail others will notice later.",
        "Let one careful improvement become the story.",
        "Sort the small pieces until the whole thing breathes.",
        "Your best answer may be practical and quiet.",
    ),
    "balance": (
        "Choose fairness without diluting your view.",
        "Keep the peace, but keep your centre too.",
        "Let grace and honesty share the same sentence.",
        "Weigh the options, then choose the cleanest truth.",
    ),
    "focus": (
        "Go deep on one thing instead of wide on ten.",
        "Protect your attention from unnecessary drama.",
        "Follow the real thread, not the brightest distraction.",
        "Let intensity become precision, not pressure.",
    ),
    "range": (
        "Follow the wider view, then bring back one lesson.",
        "Leave room for a better map than yesterday's.",
        "Let curiosity stretch the day without scattering it.",
        "Aim for meaning, then choose the next useful step.",
    ),
    "structure": (
        "Build the container before filling it.",
        "Respect the plan, but leave one hinge loose.",
        "Put the hard thing into a shape you can use.",
        "A clear boundary will save more energy than speed.",
    ),
    "perspective": (
        "Step back until the pattern becomes obvious.",
        "Give the unusual idea enough room to prove itself.",
        "Think beyond the first answer, then simplify.",
        "Let distance turn a tangle into a design.",
    ),
    "imagination": (
        "Make room for the quiet idea to speak.",
        "Let the dream become one practical note.",
        "Trust the image that keeps returning softly.",
        "Give your intuition a simple task to hold.",
    ),
}

MOON_PHASE_LINES = {
    "New Moon": (
        "Begin quietly and keep the seed protected.",
        "A private intention is stronger than a public rush.",
        "Start small; the shape will reveal itself.",
    ),
    "Waxing Crescent": (
        "Feed the thing that is just beginning to grow.",
        "Encourage the first sign of progress.",
        "Give a new plan enough light to stand up.",
    ),
    "First Quarter": (
        "A decision wants action, not another delay.",
        "Meet resistance with a clean adjustment.",
        "Choose the path that can survive contact with reality.",
    ),
    "Waxing Gibbous": (
        "Refine the work before asking it to carry more.",
        "Improve the line, not the whole drawing.",
        "Let feedback sharpen what is nearly ready.",
    ),
    "Full Moon": (
        "What was hidden may be easier to name today.",
        "Notice what has reached its natural brightness.",
        "Let clarity arrive without making it a performance.",
    ),
    "Waning Gibbous": (
        "Share the useful lesson and release the rest.",
        "Turn recent insight into a kinder habit.",
        "Let experience become guidance, not a weight.",
    ),
    "Last Quarter": (
        "Clear one stale obligation from the path.",
        "Edit the day until the useful part remains.",
        "Let go of a rule that no longer earns its place.",
    ),
    "Waning Crescent": (
        "Rest is part of the message.",
        "Close the loop gently before beginning again.",
        "Let the quiet hours do their repair work.",
    ),
}

PLANET_LINES = {
    "Mercury": (
        "Words matter, so choose the plainest true sentence.",
        "A message, note, or call can move the day forward.",
        "Keep the signal clean and the reply generous.",
    ),
    "Venus": (
        "Beauty, ease, and kindness deserve a practical place.",
        "Let agreement grow through warmth rather than pressure.",
        "Choose the option that feels graceful and real.",
    ),
    "Mars": (
        "Use force carefully; direction matters more than volume.",
        "Act cleanly, then give the room time to answer.",
        "Courage works best when it knows its target.",
    ),
    "Jupiter": (
        "A broader view brings a better choice.",
        "Let optimism be specific enough to be useful.",
        "Make space for growth without promising the impossible.",
    ),
    "Saturn": (
        "A clear limit can become a relief.",
        "Do the responsible thing in a humane way.",
        "Structure is not a cage when it protects your energy.",
    ),
}


@dataclass(frozen=True)
class AstrologyCard:
    sign: str
    sign_name: str
    date_label: str
    moon_phase: str
    skyfield_status: str
    headline: str
    body: str
    image: Image.Image
    artifact: RenderArtifact


def normalize_signs(value: Any) -> list[str]:
    if isinstance(value, str):
        raw = [part.strip().lower() for part in value.replace(";", ",").split(",")]
    elif isinstance(value, (list, tuple, set)):
        raw = [str(part).strip().lower() for part in value]
    else:
        raw = []
    selected = set(sign for sign in raw if sign in SIGN_ORDER)
    signs = [sign for sign in SIGN_ORDER if sign in selected]
    return signs or ["aries"]


def selected_sign_for_time(signs: list[str], when: datetime, interval_minutes: int) -> str:
    ordered = [sign for sign in SIGN_ORDER if sign in set(normalize_signs(signs))]
    if not ordered:
        ordered = ["aries"]
    interval_seconds = max(60, int(interval_minutes) * 60)
    block = int(when.timestamp()) // interval_seconds
    return ordered[block % len(ordered)]


def render_astrology_provider(
    output_dir: Path,
    stem: str,
    *,
    signs: list[str],
    interval_minutes: int,
    now: datetime | None = None,
) -> tuple[RenderArtifact, AstrologyCard]:
    now = now or datetime.now()
    sign = selected_sign_for_time(signs, now, interval_minutes)
    context = _planetary_context(now.date(), output_dir / "ephemeris")
    image = render_astrology_card(sign, now.date(), context)
    artifact = render_to_artifact(image, f"astrology_{sign}_{now.date().isoformat()}", [ASTROLOGY_SOURCE_URL])
    artifact.metadata.update(_metadata_for(sign, now.date(), image, context))
    write_artifact(artifact, output_dir, stem)
    card = AstrologyCard(
        sign=sign,
        sign_name=SIGN_NAMES[sign],
        date_label=_date_label(now.date()),
        moon_phase=str(context["moon_phase"]),
        skyfield_status=str(context["skyfield_status"]),
        headline=_headline_for(sign, now.date(), context),
        body=_body_for(sign, now.date(), context),
        image=image,
        artifact=artifact,
    )
    image.save(output_dir / f"{stem}.source.png")
    return artifact, card


def render_astrology_card(sign: str, day: date, context: dict[str, object] | None = None) -> Image.Image:
    sign = sign if sign in SIGN_ORDER else "aries"
    context = context or _fallback_context(day, "not requested")
    background = _load_sign_background(sign).copy()
    background = _prepare_background(background)
    _attach_protected_mask(background)
    draw = ImageDraw.Draw(background)
    red = (135, 30, 34)
    black = TEMPLATE_COLOURS["black"].rgb

    _draw_centered(background, TITLE_BOX, SIGN_NAMES[sign], red, 15, 10)
    _draw_centered(background, DATE_BOX, _date_label(day), red, 13, 10)

    headline = _headline_for(sign, day, context)
    body = _body_for(sign, day, context)
    body_width = TEXT_BOX[2] - TEXT_BOX[0] - 18
    font_head, body_lines, font_body, line_gap = _fit_horoscope_text(
        headline.upper(),
        body,
        body_width,
        TEXT_BOX[3] - TEXT_BOX[1] - 12,
    )
    y = TEXT_BOX[1] + 6
    _draw_text_centered_at_y(background, (TEXT_BOX[0] + 8, TEXT_BOX[2] - 8), y, headline.upper(), font_head, red)
    y += _text_height(font_head, headline.upper()) + 7
    for line in body_lines:
        _draw_text_centered_at_y(background, (TEXT_BOX[0] + 8, TEXT_BOX[2] - 8), y, line, font_body, black)
        y += line_gap

    phase = str(context["moon_phase"])
    _draw_centered(background, MOON_PHASE_BOX, phase, red, 13, 9)
    _draw_centered(background, FOOTER_BOX, "Ditherloom", red, 13, 9)
    return background


def _load_sign_background(sign: str) -> Image.Image:
    path = ASTROLOGY_ASSET_DIR / f"astro_{sign}.png"
    if not path.exists():
        raise FileNotFoundError(f"Astrology artwork missing for {SIGN_NAMES.get(sign, sign)}")
    image = Image.open(path).convert("RGB")
    if image.size != (WIDTH, HEIGHT):
        image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    return image


def _prepare_background(image: Image.Image) -> Image.Image:
    image = ImageEnhance.Color(image).enhance(1.20)
    image = ImageEnhance.Contrast(image).enhance(1.20)
    return image.convert("RGB")


def _attach_protected_mask(image: Image.Image) -> Image.Image:
    image.info["ditherloom_protected_mask"] = Image.new("L", image.size, 0)
    return image


def _headline_for(sign: str, day: date, context: dict[str, object] | None = None) -> str:
    element, mode, focus = SIGN_PROFILES[sign]
    moon_sign = str((context or {}).get("moon_sign") or "")
    sun_sign = str((context or {}).get("sun_sign") or "")
    visible_planet = str((context or {}).get("visible_planet") or "")
    moon_phase = str((context or {}).get("moon_phase") or "")
    options = (
        f"{focus} with grace",
        f"steady {focus}",
        f"clear {focus}",
        f"{focus} in motion",
        f"{element} wisdom, {focus}",
        f"{mode} {focus}",
        f"{moon_phase.lower()} {focus}" if moon_phase else f"{focus} in motion",
        f"{visible_planet.lower()} guides {focus}" if visible_planet else f"clear {focus}",
        f"{moon_sign.lower()} moon, {focus}" if moon_sign else f"{focus} in motion",
        f"{sun_sign.lower()} season, {focus}" if sun_sign else f"clear {focus}",
    )
    return _choice(options, sign, day, "headline")


def _body_for(sign: str, day: date, context: dict[str, object] | None = None) -> str:
    element, mode, focus = SIGN_PROFILES[sign]
    context = context or {}
    moon_sign = str(context.get("moon_sign") or "")
    moon_phase = str(context.get("moon_phase") or "")
    visible_planet = str(context.get("visible_planet") or "")
    planet_sign = str(context.get("visible_planet_sign") or "")
    core_options = (
        _choice(ELEMENT_LINES[element], sign, day, "element"),
        _choice(MODE_LINES[mode], sign, day, "mode"),
        _choice(FOCUS_LINES[focus], sign, day, "focus"),
    )
    core = _choice(core_options, sign, day, "core")
    moon_line = ""
    if moon_phase in MOON_PHASE_LINES:
        moon_line = _choice(MOON_PHASE_LINES[moon_phase], sign, day, "moon-phase")
    planet_line = ""
    if visible_planet in PLANET_LINES:
        planet_line = _choice(PLANET_LINES[visible_planet], sign, day, "planet-line")

    pattern = _daily_number(sign, day, "body-pattern") % 6
    sky_line = ""
    if moon_sign and visible_planet and planet_sign:
        sky_line = f"Moon in {moon_sign}; {visible_planet} in {planet_sign}."
    elif moon_sign:
        sky_line = f"Moon in {moon_sign}."
    if pattern == 0 and sky_line and moon_line:
        return " ".join((sky_line, moon_line, core))
    if pattern == 1 and sky_line and planet_line:
        return " ".join((sky_line, planet_line, core))
    if pattern == 2 and moon_line and planet_line:
        return " ".join((moon_line, planet_line, core))
    if pattern == 3 and sky_line:
        return " ".join((sky_line, core, _choice(FOCUS_LINES[focus], sign, day, "closing-focus")))
    if pattern == 4 and moon_line:
        return " ".join((moon_line, core))
    if planet_line:
        return " ".join((planet_line, core))
    return " ".join((sky_line, core)).strip()


def _metadata_for(sign: str, day: date, image: Image.Image, context: dict[str, object]) -> dict[str, object]:
    return {
        "provider_id": ASTROLOGY_PROVIDER_ID,
        "provider_name": ASTROLOGY_PROVIDER_NAME,
        "source": "ditherloom_local_astrology",
        "source_name": ASTROLOGY_ATTRIBUTION,
        "source_url": ASTROLOGY_SOURCE_URL,
        "attribution": ASTROLOGY_ATTRIBUTION,
        "attribution_url": ASTROLOGY_SOURCE_URL,
        "license": ASTROLOGY_LICENSE,
        "license_url": ASTROLOGY_SOURCE_URL,
        "secondary_attribution": "Skyfield and jplephem MIT libraries; NASA/JPL DE421 ephemeris data",
        "secondary_attribution_url": ASTROLOGY_EPHEMERIS_URL,
        "secondary_license": "Skyfield MIT; jplephem MIT; NASA/JPL ephemeris data retained under source terms",
        "secondary_license_url": ASTROLOGY_SKYFIELD_URL,
        "skyfield_url": ASTROLOGY_SKYFIELD_URL,
        "jplephem_url": ASTROLOGY_JPLEPHEM_URL,
        "ephemeris_url": ASTROLOGY_EPHEMERIS_URL,
        "astrology_sign": sign,
        "astrology_sign_name": SIGN_NAMES[sign],
        "astrology_date": day.isoformat(),
        "astrology_skyfield_status": context.get("skyfield_status"),
        "astrology_ephemeris": context.get("ephemeris"),
        "astrology_moon_phase": context.get("moon_phase"),
        "astrology_sun_sign": context.get("sun_sign"),
        "astrology_moon_sign": context.get("moon_sign"),
        "astrology_visible_planet": context.get("visible_planet"),
        "astrology_visible_planet_sign": context.get("visible_planet_sign"),
        "astrology_planetary_longitudes": context.get("planetary_longitudes"),
        "astrology_headline": _headline_for(sign, day, context),
        "astrology_body": _body_for(sign, day, context),
        "data_transformations": (
            "Local Ditherloom astrology V1. Horoscope copy is generated from Ditherloom-owned "
            "rules keyed by sign, date, element, modality, focus theme, and planetary/lunar "
            "positions from Skyfield/JPL ephemeris data when available. "
            "Bundled sign artwork was resized to the fixed 400x300 device canvas; the central "
            "reading area is protected as exact panel white; sign/date/footer text uses bundled "
            "Barlow regular and the horoscope headline/body text uses bundled Kalam regular. "
            "Text is pasted as crisp panel-safe solid pixels after the background pass."
        ),
    }


def _planetary_context(day: date, cache_dir: Path) -> dict[str, object]:
    try:
        from skyfield.api import Loader

        cache_dir.mkdir(parents=True, exist_ok=True)
        loader = Loader(str(cache_dir))
        timescale = loader.timescale()
        eph = loader("de421.bsp")
        t = timescale.utc(day.year, day.month, day.day, 12)
        earth = eph["earth"]
        body_keys = {
            "Sun": "sun",
            "Moon": "moon",
            "Mercury": "mercury",
            "Venus": "venus",
            "Mars": "mars",
            "Jupiter": "jupiter barycenter",
            "Saturn": "saturn barycenter",
        }
        longitudes: dict[str, float] = {}
        signs: dict[str, str] = {}
        for label, key in body_keys.items():
            apparent = earth.at(t).observe(eph[key]).apparent()
            _lat, lon, _distance = apparent.ecliptic_latlon()
            longitude = float(lon.degrees % 360)
            longitudes[label] = round(longitude, 2)
            signs[label] = _zodiac_sign(longitude)
        phase_angle = (longitudes["Moon"] - longitudes["Sun"]) % 360
        visible_planets = ("Venus", "Mars", "Mercury", "Jupiter", "Saturn")
        visible_planet = visible_planets[int(hashlib.sha256(day.isoformat().encode("utf-8")).digest()[0]) % len(visible_planets)]
        return {
            "skyfield_status": "skyfield_de421",
            "ephemeris": "JPL DE421 via Skyfield",
            "moon_phase": _moon_phase_from_angle(phase_angle),
            "sun_sign": signs["Sun"],
            "moon_sign": signs["Moon"],
            "visible_planet": visible_planet,
            "visible_planet_sign": signs[visible_planet],
            "planetary_longitudes": longitudes,
        }
    except Exception as err:
        return _fallback_context(day, f"fallback: {type(err).__name__}")


def _fallback_context(day: date, status: str) -> dict[str, object]:
    moon_index = int(((day - date(2000, 1, 6)).days / 2.46)) % len(SIGN_ORDER)
    sun_index = ((day.month + 8) % 12)
    return {
        "skyfield_status": status,
        "ephemeris": "fallback lunar approximation",
        "moon_phase": _moon_phase_name(day),
        "sun_sign": SIGN_NAMES[SIGN_ORDER[sun_index]],
        "moon_sign": SIGN_NAMES[SIGN_ORDER[moon_index]],
        "visible_planet": "",
        "visible_planet_sign": "",
        "planetary_longitudes": {},
    }


def _zodiac_sign(longitude: float) -> str:
    return SIGN_NAMES[SIGN_ORDER[int(longitude // 30) % 12]]


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


def _choice(values: tuple[str, ...], sign: str, day: date, salt: str) -> str:
    return values[_daily_number(sign, day, salt) % len(values)]


def _daily_number(sign: str, day: date, salt: str) -> int:
    digest = hashlib.sha256(f"{sign}:{day.isoformat()}:{salt}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def _date_label(day: date) -> str:
    suffix = "th"
    if day.day % 100 not in (11, 12, 13):
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day.day % 10, "th")
    return f"{day.day}{suffix} {day.strftime('%b')}"


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_REGULAR), size)
    except OSError:
        return ImageFont.load_default()


def _body_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_BODY), size)
    except OSError:
        return _font(size)


def _font_that_fits(text: str, width: int, start: int, minimum: int) -> ImageFont.ImageFont:
    for size in range(start, minimum - 1, -1):
        font = _font(size)
        left, top, right, bottom = font.getbbox(text)
        if right - left <= width and bottom - top <= 28:
            return font
    return _font(minimum)


def _body_font_that_fits(text: str, width: int, start: int, minimum: int) -> ImageFont.ImageFont:
    for size in range(start, minimum - 1, -1):
        font = _body_font(size)
        left, top, right, bottom = font.getbbox(text)
        if right - left <= width and bottom - top <= 30:
            return font
    return _body_font(minimum)


def _fit_horoscope_text(
    headline: str,
    body: str,
    width: int,
    height: int,
) -> tuple[ImageFont.ImageFont, list[str], ImageFont.ImageFont, int]:
    for body_size in range(19, 13, -1):
        body_font = _body_font(body_size)
        body_lines = _wrap_text_to_width(body, body_font, width)
        if len(body_lines) > BODY_MAX_LINES:
            continue
        body_line_gap = max(17, _text_height(body_font, "Ag") + 4)
        for headline_size in range(24, 15, -1):
            headline_font = _body_font(headline_size)
            if headline_font.getlength(headline) > width:
                continue
            total_height = _text_height(headline_font, headline) + 7 + len(body_lines) * body_line_gap
            if total_height <= height:
                return headline_font, body_lines, body_font, body_line_gap

    body_font = _body_font(14)
    body_lines = _wrap_text_to_width(body, body_font, width)
    if len(body_lines) > BODY_MAX_LINES:
        body_lines = body_lines[:BODY_MAX_LINES]
        body_lines[-1] = _ellipsize_to_width(body_lines[-1], body_font, width)
    headline_font = _body_font_that_fits(headline, width, 20, 15)
    return headline_font, body_lines, body_font, max(16, _text_height(body_font, "Ag") + 3)


def _text_height(font: ImageFont.ImageFont, text: str) -> int:
    top = font.getbbox(text)[1]
    bottom = font.getbbox(text)[3]
    return bottom - top


def _draw_centered(
    image: Image.Image,
    box: tuple[int, int, int, int],
    text: str,
    fill: tuple[int, int, int],
    start_size: int,
    min_size: int,
) -> None:
    font = _font_that_fits(text, box[2] - box[0], start_size, min_size)
    left, top, right, bottom = font.getbbox(text)
    x = box[0] + (box[2] - box[0] - (right - left)) / 2 - left
    y = box[1] + (box[3] - box[1] - (bottom - top)) / 2 - top
    _draw_crisp_text(image, (int(x), int(y)), text, font, fill)


def _draw_text_centered_at_y(
    image: Image.Image,
    x_bounds: tuple[int, int],
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    left, _top, right, _bottom = font.getbbox(text)
    width = right - left
    x = x_bounds[0] + (x_bounds[1] - x_bounds[0] - width) / 2 - left
    _draw_crisp_text(image, (int(x), y), text, font, fill)


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


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _body_lines_that_fit(text: str, width: int, max_lines: int) -> tuple[list[str], ImageFont.ImageFont]:
    for size in range(20, 15, -1):
        font = _body_font(size)
        lines = _wrap_text_to_width(text, font, width)
        if len(lines) <= max_lines:
            return lines, font
    font = _body_font(16)
    lines = _wrap_text_to_width(text, font, width)
    if len(lines) <= max_lines:
        return lines, font
    fitted = lines[:max_lines]
    fitted[-1] = _ellipsize_to_width(fitted[-1], font, width)
    return fitted, font


def _wrap_text_to_width(text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
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
            else:
                lines.append(_ellipsize_to_width(word, font, width))
                current = ""
    if current:
        lines.append(current)
    return lines


def _ellipsize_to_width(text: str, font: ImageFont.ImageFont, width: int) -> str:
    suffix = "..."
    candidate = text
    while candidate:
        if font.getlength(candidate + suffix) <= width:
            return candidate.rstrip() + suffix
        candidate = candidate[:-1]
    return suffix
