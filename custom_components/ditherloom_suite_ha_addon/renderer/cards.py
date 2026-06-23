from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .palette import TEMPLATE_COLOURS

WIDTH = 400
HEIGHT = 300
TOP_BAR_HEIGHT = 38
BOTTOM_BAR_HEIGHT = 38
FONT_SCALE = 1.4
GLYPH_ROWS = 7
GLYPH_COLS = 5

COLOUR_MODE_COLOUR = "colour"
COLOUR_MODE_MONO = "mono"

FONT_CANDIDATES = (
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/bahnschrift.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)
FONT_REGULAR_CANDIDATES = (
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)
WEATHER_ART_DIR = Path(__file__).resolve().parents[1] / "assets" / "weather_art"
WEATHER_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "assets" / "weather_templates" / "safe_400x300"


@dataclass(frozen=True)
class WeatherCardData:
    location: str = "Home"
    condition: str = "Sunny"
    temperature: str = "22"
    unit: str = "C"
    high: str = "26"
    low: str = "16"
    rain: str = "10%"
    wind: str = "9 km/h"
    updated: str = "Now"
    alert: str = ""
    source_entity_id: str = "weather.home"
    humidity: str = ""
    uv_index: str = ""
    feels_like: str = ""
    pressure: str = ""
    details: tuple[tuple[str, str], ...] = ()


GLYPHS: dict[str, tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10011", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


def _scaled(size: int) -> int:
    return max(1, int(round(size * FONT_SCALE)))


def _load_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    candidates = FONT_CANDIDATES if bold else FONT_REGULAR_CANDIDATES
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_font(text: str, max_width: int, max_height: int, start_size: int, min_size: int = 8, bold: bool = True) -> ImageFont.ImageFont:
    value = str(text)
    for size in range(start_size, min_size - 1, -1):
        font = _load_font(size, bold=bold)
        left, top, right, bottom = font.getbbox(value)
        if right - left <= max_width and bottom - top <= max_height:
            return font
    return _load_font(min_size, bold=bold)


def _draw_font_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fill: tuple[int, int, int],
    size: int,
    min_size: int = 8,
    bold: bool = True,
) -> None:
    x1, y1, x2, y2 = box
    value = str(text)
    font = _fit_font(value, x2 - x1 - 6, y2 - y1 - 4, size, min_size=min_size, bold=bold)
    left, top, right, bottom = font.getbbox(value)
    width = right - left
    height = bottom - top
    x = x1 + (x2 - x1 - width) / 2 - left
    y = y1 + (y2 - y1 - height) / 2 - top
    draw.text((int(x), int(y)), value, font=font, fill=fill)


def _draw_safe_gradient(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    names: tuple[str, ...],
    vertical: bool = False,
) -> None:
    if not names:
        return
    x1, y1, x2, y2 = box
    span = max(1, (y2 - y1) if vertical else (x2 - x1))
    stops = [_rgb(name) for name in names]
    for i in range(span + 1):
        pos = i / span
        scaled = pos * (len(stops) - 1)
        index = min(len(stops) - 2, int(scaled)) if len(stops) > 1 else 0
        frac = scaled - index if len(stops) > 1 else 0
        c1 = stops[index]
        c2 = stops[min(index + 1, len(stops) - 1)]
        colour = tuple(int(c1[channel] + (c2[channel] - c1[channel]) * frac) for channel in range(3))
        if vertical:
            draw.line((x1, y1 + i, x2, y1 + i), fill=colour)
        else:
            draw.line((x1 + i, y1, x1 + i, y2), fill=colour)


def _draw_photo_sun(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], variant: str, colours: dict[str, object]) -> None:
    x1, y1, x2, y2 = box
    cx = (x1 + x2) // 2
    cy = y1 + 38
    radius = 20 if variant == "small" else 26
    for r in range(72, radius, -4):
        alpha_name = ("pale_yellow", "cream", "bright_yellow", "yellow", "gold")[min(4, max(0, (72 - r) // 12))]
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=_rgb(alpha_name))
    for angle in range(0, 360, 8):
        length = 70 if angle % 24 else 95
        x_end = cx + int(math.cos(math.radians(angle)) * length)
        y_end = cy + int(math.sin(math.radians(angle)) * length)
        draw.line((cx, cy, x_end, y_end), fill=_rgb("pale_yellow"), width=1)
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=_rgb("bright_yellow"))
    draw.ellipse((cx - radius + 7, cy - radius + 7, cx + radius - 7, cy + radius - 7), fill=_rgb("yellow"))
    draw.ellipse((cx - radius + 16, cy - radius + 16, cx + radius - 16, cy + radius - 16), fill=_rgb("orange"))
    ground_y = y2 - 22
    for offset, name in enumerate(("parchment", "tan", "gold", "pale_yellow")):
        draw.arc((x1 - 40 + offset * 12, ground_y - 48 + offset * 6, x2 + 40 - offset * 12, ground_y + 38), 185, 355, fill=_rgb(name), width=3)
    for x in range(x1, x2, 16):
        draw.line((x, ground_y, x + 30, y2), fill=_rgb("tan"), width=1)


def _draw_photo_cloud(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], storm: bool = False, rain: bool = False) -> None:
    x1, y1, x2, y2 = box
    cx = (x1 + x2) // 2
    cy = y1 + 54
    shades = ("linen", "paper", "warm_white", "pale_cream") if not storm else ("warm_grey", "linen", "paper", "rose")
    for index, (dx, dy, rx, ry) in enumerate(((-45, 5, 42, 32), (-10, -18, 50, 42), (38, 2, 46, 34), (0, 14, 88, 34))):
        name = shades[min(index, len(shades) - 1)]
        draw.ellipse((cx + dx - rx, cy + dy - ry, cx + dx + rx, cy + dy + ry), fill=_rgb(name))
    for index in range(0, 6):
        y = cy + 28 + index * 7
        draw.line((cx - 82 + index * 6, y, cx + 86 - index * 5, y), fill=_rgb("warm_grey" if storm else "linen"), width=2)
    if rain:
        for dx in range(-54, 60, 18):
            draw.line((cx + dx, cy + 60, cx + dx - 9, cy + 104), fill=_rgb("warm_grey"), width=3)
    if storm:
        bolt = [(cx + 8, cy + 44), (cx - 14, cy + 92), (cx + 8, cy + 84), (cx - 2, cy + 126), (cx + 36, cy + 68), (cx + 12, cy + 76)]
        draw.polygon(bolt, fill=_rgb("bright_yellow"))
        draw.line(bolt + [bolt[0]], fill=_rgb("black"), width=2)


def _draw_photo_weather_art(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], kind: str, title: str, colours: dict[str, object]) -> None:
    artwork = _weather_art_for_title(title, kind)
    if artwork is None:
        _draw_safe_gradient(draw, box, ("warm_white", "cream", "pale_cream"), vertical=True)
        return
    x1, y1, x2, y2 = box
    target_w = x2 - x1
    target_h = y2 - y1
    scale = max(target_w / artwork.width, target_h / artwork.height)
    resized = artwork.resize((max(1, int(artwork.width * scale)), max(1, int(artwork.height * scale))), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - target_w) // 2)
    top = max(0, (resized.height - target_h) // 2)
    cropped = resized.crop((left, top, left + target_w, top + target_h))
    draw._image.paste(cropped, (x1, y1))


@lru_cache(maxsize=24)
def _load_weather_art(name: str) -> Image.Image | None:
    path = WEATHER_ART_DIR / f"{name}.png"
    if not path.exists():
        return None
    return Image.open(path).convert("RGB")


def _weather_art_for_title(title: str, kind: str) -> Image.Image | None:
    normalized = title.lower()
    is_night = "night" in normalized
    if "storm" in normalized or "thunder" in normalized or "hail" in normalized or kind == "storm":
        return _load_weather_art("storm_night" if is_night else "storm_day")
    if "rain" in normalized or "drizzle" in normalized or "shower" in normalized or kind == "rain":
        return _load_weather_art("rain_night" if is_night else "rain_day")
    if "partly" in normalized:
        return _load_weather_art("partly_cloudy_night" if is_night else "partly_cloudy_day")
    if "cloud" in normalized or "overcast" in normalized:
        return _load_weather_art("cloudy_night" if is_night else "cloudy_day")
    if "fog" in normalized:
        return _load_weather_art("cloudy_night" if is_night else "cloudy_day")
    if "snow" in normalized or "freezing" in normalized or "cold" in normalized or "wind" in normalized:
        return _load_weather_art("cloudy_night" if is_night else "cloudy_day")
    if is_night or "clear night" in normalized:
        return _load_weather_art("clear_night")
    return _load_weather_art("sunny_day")


def _modern_kind(condition: str, alert: str) -> str:
    return _condition_kind(condition, alert)


@lru_cache(maxsize=32)
def _load_weather_template(slug: str) -> Image.Image | None:
    path = WEATHER_TEMPLATE_DIR / f"{slug}_template_30safe_400x300.png"
    if not path.exists():
        return None
    return Image.open(path).convert("RGB")


def _has_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _template_slug_for_data(data: WeatherCardData) -> str:
    title = f"{data.alert} {data.condition}".strip().lower()
    is_night = "night" in title

    if _has_any(title, "bushfire", "fire risk"):
        return "bushfire_risk_day"
    if _has_any(title, "extreme heat", "heatwave"):
        return "extreme_heat_day"
    if _has_any(title, "extreme cold", "freezing"):
        return "extreme_cold_day"
    if _has_any(title, "hail"):
        return "storm_night" if is_night else "hail_storm_day"
    if _has_any(title, "snow", "sleet"):
        return "cloudy_night" if is_night else "snow_day"
    if _has_any(title, "high wind", "wind warning", "gale"):
        return "cloudy_night" if is_night else "high_wind_day"
    if _has_any(title, "storm", "thunder", "lightning"):
        return "storm_night" if is_night else "storm_day"
    if _has_any(title, "heavy rain", "rain", "drizzle", "showers", "shower"):
        return "rain_night" if is_night else "rain_day"
    if _has_any(title, "fog", "mist", "haze"):
        return "cloudy_night" if is_night else "fog_day"
    if _has_any(title, "partly"):
        return "partly_cloudy_night" if is_night else "partly_cloudy_day"
    if _has_any(title, "cloud", "overcast"):
        return "cloudy_night" if is_night else "cloudy_day"
    if is_night or _has_any(title, "clear night"):
        return "clear_night"
    return "sunny_day"


def _draw_template_value(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    value: str,
    start_size: int = 22,
    min_size: int = 11,
) -> None:
    colours = {"text": "black"}
    _draw_centred_text(draw, box, value, start_size, colours, "text", True, min_size)


def _fit_tight_bitmap_scale(text: str, max_width: int, max_height: int, size: int, min_size: int) -> int:
    current = max(1, int(round(size / GLYPH_ROWS)))
    min_scale = max(1, int(round(min_size / GLYPH_ROWS)))
    while current >= min_scale:
        width, height = _bitmap_size(text, current, spacing=0)
        if width <= max_width and height <= max_height:
            return current
        current -= 1
    return min_scale


def _draw_tight_centred_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: object,
    size: int,
    fill: tuple[int, int, int],
    min_size: int = 10,
) -> None:
    x1, y1, x2, y2 = box
    normalized = _normalize_text(text)
    scale = _fit_tight_bitmap_scale(normalized, x2 - x1 - 2, y2 - y1 - 2, _scaled(size), min_size)
    width, height = _bitmap_size(normalized, scale, spacing=0)
    x = int(x1 + (x2 - x1 - width) / 2)
    y = int(y1 + (y2 - y1 - height) / 2)
    cursor = x
    for char in normalized:
        glyph = _glyph(char)
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    px = cursor + col * scale
                    py = y + row * scale
                    cx1 = max(px, x1)
                    cy1 = max(py, y1)
                    cx2 = min(px + scale - 1, x2 - 1)
                    cy2 = min(py + scale - 1, y2 - 1)
                    if cx1 <= cx2 and cy1 <= cy2:
                        draw.rectangle((cx1, cy1, cx2, cy2), fill=fill)
        cursor += GLYPH_COLS * scale


def _draw_template_metric(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    accent: str,
) -> None:
    x1, y1, x2, y2 = box
    label_width = 27
    draw.rectangle(box, fill=_rgb("white"), outline=_rgb("black"), width=1)
    draw.rectangle((x1, y1, x1 + label_width, y2), fill=_rgb(accent), outline=_rgb("black"), width=1)
    draw.line((x1 + label_width, y1, x1 + label_width, y2), fill=_rgb("black"), width=1)
    _draw_tight_centred_text(draw, (x1 + 2, y1 + 2, x1 + label_width - 1, y2 - 2), label[:2].upper(), 21, _rgb("black"), 12)
    compact_value = value
    if label.upper() == "WI":
        compact_value = value.replace("km/h", "KM/H").replace("mph", "MPH")
    start_size = 21 if label.upper() in {"PR", "WI"} else 23
    min_size = 12 if label.upper() in {"PR", "WI"} else 13
    _draw_tight_centred_text(draw, (x1 + label_width + 2, y1 + 2, x2 - 3, y2 - 2), compact_value, start_size, _rgb("black"), min_size)


def _render_template_weather_card(data: WeatherCardData) -> Image.Image | None:
    slug = _template_slug_for_data(data)
    template = _load_weather_template(slug)
    if template is None:
        template = _load_weather_template("sunny_day")
    if template is None:
        return None

    image = template.copy()
    draw = ImageDraw.Draw(image)
    text_colours = {
        "text": "black",
        "top_text": "black",
        "bottom_text": "black",
        "inverse_text": "bright_yellow",
    }

    title = (data.alert.strip() or data.condition.strip() or "Weather").upper()
    _draw_centred_text(draw, (8, 0, WIDTH - 8, TOP_BAR_HEIGHT), title, 28, text_colours, "top_text", True, 14)
    _draw_centred_text(
        draw,
        (8, HEIGHT - BOTTOM_BAR_HEIGHT, WIDTH - 8, HEIGHT),
        (data.location or "Weather location").upper(),
        25,
        text_colours,
        "bottom_text",
        True,
        12,
    )

    left_metrics = (
        ("UV", _detail_value(data, ("UV", "uv_index"), data.uv_index), (4, 50, 110, 84), "pale_yellow"),
        ("RA", _detail_value(data, ("Rain",), data.rain), (4, 99, 110, 133), "rose"),
        ("PR", data.pressure or "--", (4, 148, 110, 182), "peach"),
    )
    right_metrics = (
        ("HI", f"{data.high}{data.unit}", (290, 50, 396, 84), "pale_yellow"),
        ("LO", f"{data.low}{data.unit}", (290, 99, 396, 133), "pale_yellow"),
        ("HU", _detail_value(data, ("Hum", "Humidity"), data.humidity), (290, 148, 396, 182), "pale_yellow"),
        ("WI", _detail_value(data, ("Wind",), data.wind), (290, 197, 396, 231), "tan"),
    )
    for label, value, box, accent in left_metrics + right_metrics:
        _draw_template_metric(draw, box, label, value, accent)

    draw.rectangle((129, 170, 271, 236), fill=_rgb("black"), outline=_rgb("black"), width=1)
    _draw_centred_text(
        draw,
        (131, 170, 269, 236),
        f"{data.temperature}{data.unit}",
        52,
        text_colours,
        "inverse_text",
        True,
        30,
    )
    feels_like = f"Feels Like {data.feels_like}" if data.feels_like else "Feels Like --"
    draw.rectangle((96, 238, 304, 260), fill=_rgb("white"), outline=_rgb("black"), width=1)
    _draw_centred_text(draw, (98, 239, 302, 259), feels_like, 18, text_colours, "text", True, 10)
    return image


def _modern_bar_steps(kind: str, alert: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    normalized = alert.lower()
    if "storm" in normalized or "hail" in normalized or kind == "storm":
        return ("rose", "warm_red", "red"), ("rose", "warm_red", "red")
    if "rain" in normalized or kind == "rain":
        return ("rose", "blush", "peach"), ("rose", "warm_red", "peach")
    if "cloud" in normalized or kind == "cloud":
        return ("warm_white", "pale_cream", "parchment"), ("warm_white", "parchment", "tan")
    return ("bright_yellow", "pale_yellow", "peach", "warm_red"), ("bright_yellow", "gold", "peach", "red")


def _draw_modern_metric(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str, value: str, accent: str) -> None:
    x1, y1, x2, y2 = box
    label_w = max(24, int((x2 - x1) * 0.34))
    draw.rectangle(box, fill=_rgb("warm_white"), outline=_rgb("black"), width=1)
    _draw_safe_gradient(draw, (x1, y1, x1 + label_w, y2), ("pale_yellow", accent))
    draw.line((x1 + label_w, y1, x1 + label_w, y2), fill=_rgb("black"), width=1)
    _draw_font_text(draw, (x1 + 2, y1, x1 + label_w - 1, y2), label.upper()[:2], _rgb("black"), 19, 11, True)
    _draw_font_text(draw, (x1 + label_w + 3, y1, x2 - 3, y2), value, _rgb("black"), 19, 10, True)


def render_modern_weather_card(data: WeatherCardData, colour_mode: str = COLOUR_MODE_COLOUR) -> Image.Image:
    if _is_mono(colour_mode):
        return render_weather_card(data, colour_mode=colour_mode)

    template_card = _render_template_weather_card(data)
    if template_card is not None:
        return template_card

    kind = _modern_kind(data.condition, data.alert)
    colours = _colours(kind, colour_mode)
    title = (data.alert or data.condition or "Weather").upper()
    image = Image.new("RGB", (WIDTH, HEIGHT), _rgb("warm_white"))
    draw = ImageDraw.Draw(image)

    top_steps, bottom_steps = _modern_bar_steps(kind, data.alert or data.condition)
    _draw_safe_gradient(draw, (0, 0, WIDTH - 1, TOP_BAR_HEIGHT), top_steps)
    _draw_safe_gradient(draw, (0, HEIGHT - BOTTOM_BAR_HEIGHT, WIDTH - 1, HEIGHT - 1), bottom_steps)
    draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=_rgb("black"), width=1)
    draw.line((0, TOP_BAR_HEIGHT, WIDTH, TOP_BAR_HEIGHT), fill=_rgb("black"), width=1)
    draw.line((0, HEIGHT - BOTTOM_BAR_HEIGHT, WIDTH, HEIGHT - BOTTOM_BAR_HEIGHT), fill=_rgb("black"), width=1)
    _draw_font_text(draw, (8, 2, WIDTH - 8, TOP_BAR_HEIGHT - 2), title, _rgb("black"), 30, 16, True)
    _draw_font_text(draw, (8, HEIGHT - BOTTOM_BAR_HEIGHT + 2, WIDTH - 8, HEIGHT - 3), (data.location or "Weather location").upper(), _rgb("black"), 27, 14, True)

    body = Image.new("RGB", (WIDTH, HEIGHT - TOP_BAR_HEIGHT - BOTTOM_BAR_HEIGHT - 2), _rgb("warm_white"))
    body_draw = ImageDraw.Draw(body)
    _draw_safe_gradient(body_draw, (0, 0, WIDTH - 1, body.height - 1), ("warm_white", "cream", "warm_white"), vertical=True)
    body = body.filter(ImageFilter.GaussianBlur(0.25))
    image.paste(body, (0, TOP_BAR_HEIGHT + 1))
    draw = ImageDraw.Draw(image)

    art_box = (96, 46, 304, 184)
    _draw_photo_weather_art(draw, art_box, kind, title, colours)

    left_metrics = (
        ("UV", _detail_value(data, ("UV", "uv_index"), data.uv_index), "pale_yellow"),
        ("RA", _detail_value(data, ("Rain",), data.rain), "peach"),
        ("PR", data.pressure or "--", "orange"),
    )
    right_metrics = (
        ("HI", f"{data.high}{data.unit}", "pale_yellow"),
        ("LO", f"{data.low}{data.unit}", "pale_yellow"),
        ("HU", _detail_value(data, ("Hum", "Humidity"), data.humidity), "pale_yellow"),
        ("WI", _detail_value(data, ("Wind",), data.wind), "pale_yellow"),
    )
    for y, (label, value, accent) in zip((50, 100, 150), left_metrics):
        _draw_modern_metric(draw, (12, y, 84, y + 32), label, value, accent)
    for y, (label, value, accent) in zip((50, 96, 142, 188), right_metrics):
        _draw_modern_metric(draw, (316, y, 388, y + 32), label, value, accent)

    temp_box = (130, 176, 270, 242)
    draw.rectangle(temp_box, fill=_rgb("black"))
    _draw_font_text(draw, temp_box, f"{data.temperature}{data.unit}", _rgb("bright_yellow"), 61, 30, True)
    feels_like = f"Feels Like {data.feels_like}" if data.feels_like else "Feels Like --"
    _draw_font_text(draw, (92, 238, 308, HEIGHT - BOTTOM_BAR_HEIGHT - 2), feels_like, _rgb("black"), 19, 11, True)
    return image


def _normalize_text(text: object) -> str:
    return str(text).upper().replace("°", "").replace("_", "-")


def _glyph(char: str) -> tuple[str, ...]:
    return GLYPHS.get(char, GLYPHS[" "])


def _bitmap_size(text: str, scale: int, spacing: int | None = None) -> tuple[int, int]:
    spacing = scale if spacing is None else spacing
    if not text:
        return 0, GLYPH_ROWS * scale
    width = len(text) * GLYPH_COLS * scale + max(0, len(text) - 1) * spacing
    return width, GLYPH_ROWS * scale


def _fit_bitmap_scale(text: str, max_width: int, max_height: int, size: int, min_size: int) -> int:
    current = max(1, int(round(size / GLYPH_ROWS)))
    min_scale = max(1, int(round(min_size / GLYPH_ROWS)))
    while current >= min_scale:
        width, height = _bitmap_size(text, current)
        if width <= max_width and height <= max_height:
            return current
        current -= 1
    return min_scale


def _draw_bitmap_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: object, scale: int, fill: tuple[int, int, int]) -> None:
    normalized = _normalize_text(text)
    x, y = xy
    spacing = scale
    for char in normalized:
        glyph = _glyph(char)
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    x1 = x + col * scale
                    y1 = y + row * scale
                    draw.rectangle((x1, y1, x1 + scale - 1, y1 + scale - 1), fill=fill)
        x += GLYPH_COLS * scale + spacing


def _draw_centred_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    size: int,
    colours: dict[str, str],
    fill_name: str = "text",
    bold: bool = True,
    min_size: int = 10,
) -> None:
    x1, y1, x2, y2 = box
    normalized = _normalize_text(text)
    scale = _fit_bitmap_scale(normalized, x2 - x1 - 8, y2 - y1 - 4, _scaled(size), min_size)
    width, height = _bitmap_size(normalized, scale)
    _draw_bitmap_text(
        draw,
        (int(x1 + (x2 - x1 - width) / 2), int(y1 + (y2 - y1 - height) / 2)),
        normalized,
        scale,
        _rgb(colours[fill_name]),
    )


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int,
    colours: dict[str, str],
    fill_name: str = "text",
    bold: bool = False,
    max_width: int | None = None,
    min_size: int = 10,
) -> None:
    normalized = _normalize_text(text)
    if max_width:
        scale = _fit_bitmap_scale(normalized, max_width, GLYPH_ROWS * _scaled(size), _scaled(size), min_size)
    else:
        scale = max(1, int(round(_scaled(size) / GLYPH_ROWS)))
    _draw_bitmap_text(draw, xy, normalized, scale, _rgb(colours[fill_name]))


def _rgb(name: str) -> tuple[int, int, int]:
    return TEMPLATE_COLOURS[name].rgb


def _colour_names(colours: dict[str, object], key: str) -> tuple[str, ...]:
    value = colours.get(key, ())
    if isinstance(value, str):
        return (value,)
    return tuple(str(name) for name in value)


def _colour_name(colours: dict[str, object], key: str, fallback: str) -> str:
    value = colours.get(key, fallback)
    return value if isinstance(value, str) else fallback


def _is_mono(colour_mode: str) -> bool:
    return str(colour_mode).lower() in {COLOUR_MODE_MONO, "black_white", "black-and-white", "bw", "b&w"}


def _condition_kind(condition: str, alert: str) -> str:
    normalized = f"{condition} {alert}".lower()
    if "bushfire" in normalized or "fire" in normalized or "extreme heat" in normalized:
        return "sun"
    if "storm" in normalized or "thunder" in normalized or "hail" in normalized:
        return "storm"
    if "rain" in normalized or "shower" in normalized or "drizzle" in normalized:
        return "rain"
    if "snow" in normalized or "freezing" in normalized or "ice" in normalized or "extreme cold" in normalized:
        return "cloud"
    if "wind" in normalized:
        return "cloud"
    if "night" in normalized:
        return "night"
    if "cloud" in normalized or "overcast" in normalized or "fog" in normalized:
        return "cloud"
    return "sun"


def _colours(kind: str, colour_mode: str) -> dict[str, object]:
    if _is_mono(colour_mode):
        return {
            "background": "white",
            "texture": "white",
            "top": "black",
            "top_text": "white",
            "bottom": "black",
            "bottom_text": "white",
            "panel": "white",
            "symbol_panel": "white",
            "symbol_fill": "white",
            "symbol_accent": "black",
            "metric": "white",
            "metric_accent": "black",
            "metric_text": "black",
            "text": "black",
            "inverse_text": "white",
            "outline": "black",
            "top_steps": ("black",),
            "bottom_steps": ("black",),
            "body_steps": ("white",),
            "metric_accents": ("black",),
            "symbol_shades": ("white",),
        }

    if kind == "storm":
        return {
            "background": "paper",
            "texture": "blush",
            "top": "peach",
            "top_text": "black",
            "bottom": "peach",
            "bottom_text": "black",
            "panel": "white",
            "symbol_panel": "warm_red",
            "symbol_fill": "white",
            "symbol_accent": "bright_yellow",
            "metric": "white",
            "metric_accent": "red",
            "metric_text": "black",
            "text": "black",
            "inverse_text": "white",
            "outline": "black",
            "top_steps": ("peach", "blush", "rose", "pale_cream", "warm_white", "bright_yellow"),
            "bottom_steps": ("bright_yellow", "cream", "pale_cream", "blush", "peach"),
            "body_steps": ("warm_white", "blush", "pale_cream", "cream", "peach"),
            "metric_accents": ("red", "orange", "dark_red", "maroon", "gold", "warm_red"),
            "symbol_shades": ("warm_red", "rose", "blush", "white"),
        }
    if kind == "cloud":
        return {
            "background": "cream",
            "texture": "pale_yellow",
            "top": "cream",
            "top_text": "black",
            "bottom": "cream",
            "bottom_text": "black",
            "panel": "white",
            "symbol_panel": "white",
            "symbol_fill": "paper",
            "symbol_accent": "bright_yellow",
            "metric": "white",
            "metric_accent": "bright_yellow",
            "metric_text": "black",
            "text": "black",
            "inverse_text": "bright_yellow",
            "outline": "black",
            "top_steps": ("cream", "pale_yellow", "warm_white", "tan", "bright_yellow"),
            "bottom_steps": ("bright_yellow", "pale_yellow", "cream", "warm_white", "parchment"),
            "body_steps": ("warm_white", "paper", "pale_cream", "cream", "parchment"),
            "metric_accents": ("warm_grey", "dark_gold", "gold", "yellow", "tan", "pale_yellow"),
            "symbol_shades": ("paper", "linen", "warm_white", "cream"),
        }
    if kind == "rain":
        return {
            "background": "white",
            "texture": "pale_cream",
            "top": "bright_yellow",
            "top_text": "black",
            "bottom": "bright_yellow",
            "bottom_text": "black",
            "panel": "white",
            "symbol_panel": "pale_cream",
            "symbol_fill": "white",
            "symbol_accent": "bright_yellow",
            "metric": "white",
            "metric_accent": "bright_yellow",
            "metric_text": "black",
            "text": "black",
            "inverse_text": "bright_yellow",
            "outline": "black",
            "top_steps": ("bright_yellow", "pale_yellow", "cream", "tan", "gold"),
            "bottom_steps": ("gold", "tan", "cream", "pale_yellow", "bright_yellow"),
            "body_steps": ("pale_cream", "paper", "warm_white", "cream", "parchment"),
            "metric_accents": ("gold", "tan", "yellow", "dark_gold", "warm_grey", "bright_yellow"),
            "symbol_shades": ("pale_cream", "paper", "white", "parchment"),
        }
    if kind == "night":
        return {
            "background": "warm_white",
            "texture": "pale_yellow",
            "top": "bright_yellow",
            "top_text": "black",
            "bottom": "bright_yellow",
            "bottom_text": "black",
            "panel": "white",
            "symbol_panel": "warm_white",
            "symbol_fill": "bright_yellow",
            "symbol_accent": "red",
            "metric": "white",
            "metric_accent": "bright_yellow",
            "metric_text": "black",
            "text": "black",
            "inverse_text": "bright_yellow",
            "outline": "black",
            "top_steps": ("warm_white", "pale_yellow", "cream", "parchment", "bright_yellow"),
            "bottom_steps": ("bright_yellow", "parchment", "cream", "pale_yellow", "warm_white"),
            "body_steps": ("warm_white", "paper", "pale_cream", "cream", "parchment"),
            "metric_accents": ("bright_yellow", "gold", "dark_gold", "burgundy", "warm_red", "yellow"),
            "symbol_shades": ("warm_white", "pale_yellow", "bright_yellow", "gold"),
        }
    return {
        "background": "warm_white",
        "texture": "pale_yellow",
        "top": "bright_yellow",
        "top_text": "black",
        "bottom": "bright_yellow",
        "bottom_text": "black",
        "panel": "white",
        "symbol_panel": "pale_yellow",
        "symbol_fill": "bright_yellow",
        "symbol_accent": "red",
        "metric": "white",
        "metric_accent": "bright_yellow",
        "metric_text": "black",
        "text": "black",
        "inverse_text": "bright_yellow",
        "outline": "black",
        "top_steps": ("bright_yellow", "yellow", "gold", "orange", "burnt_orange", "bright_yellow"),
        "bottom_steps": ("dark_gold", "gold", "yellow", "pale_yellow", "cream", "bright_yellow"),
        "body_steps": ("warm_white", "pale_yellow", "cream", "parchment", "tan", "pale_cream"),
        "metric_accents": ("red", "orange", "burnt_orange", "gold", "yellow", "dark_gold"),
        "symbol_shades": ("bright_yellow", "yellow", "gold", "orange", "pale_yellow"),
    }


def _draw_stepped_fill(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    names: tuple[str, ...],
    vertical: bool = False,
) -> None:
    if not names:
        return
    x1, y1, x2, y2 = box
    length = max(1, (y2 - y1 + 1) if vertical else (x2 - x1 + 1))
    step = max(1, math.ceil(length / len(names)))
    for index, name in enumerate(names):
        if vertical:
            sy1 = y1 + index * step
            sy2 = y2 if index == len(names) - 1 else min(y2, sy1 + step - 1)
            draw.rectangle((x1, sy1, x2, sy2), fill=_rgb(name))
        else:
            sx1 = x1 + index * step
            sx2 = x2 if index == len(names) - 1 else min(x2, sx1 + step - 1)
            draw.rectangle((sx1, y1, sx2, y2), fill=_rgb(name))


def _draw_bars(draw: ImageDraw.ImageDraw, data: WeatherCardData, colours: dict[str, object]) -> None:
    top_steps = _colour_names(colours, "top_steps")
    bottom_steps = _colour_names(colours, "bottom_steps")
    if len(top_steps) > 1:
        _draw_stepped_fill(draw, (0, 0, WIDTH, TOP_BAR_HEIGHT), top_steps)
    else:
        draw.rectangle((0, 0, WIDTH, TOP_BAR_HEIGHT), fill=_rgb(_colour_name(colours, "top", "black")))
    if len(bottom_steps) > 1:
        _draw_stepped_fill(draw, (0, HEIGHT - BOTTOM_BAR_HEIGHT, WIDTH, HEIGHT), bottom_steps)
    else:
        draw.rectangle((0, HEIGHT - BOTTOM_BAR_HEIGHT, WIDTH, HEIGHT), fill=_rgb(_colour_name(colours, "bottom", "black")))
    draw.line((0, TOP_BAR_HEIGHT, WIDTH, TOP_BAR_HEIGHT), fill=_rgb("black"), width=4)
    draw.line((0, HEIGHT - BOTTOM_BAR_HEIGHT, WIDTH, HEIGHT - BOTTOM_BAR_HEIGHT), fill=_rgb("black"), width=4)
    title = data.alert.strip() or data.condition.strip() or "Weather"
    _draw_centred_text(draw, (8, 0, WIDTH - 8, TOP_BAR_HEIGHT), title.upper(), 27, colours, "top_text", True, 14)
    _draw_centred_text(
        draw,
        (8, HEIGHT - BOTTOM_BAR_HEIGHT, WIDTH - 8, HEIGHT),
        (data.location or "Weather location").upper(),
        24,
        colours,
        "bottom_text",
        True,
        12,
    )


def _draw_texture(draw: ImageDraw.ImageDraw, colours: dict[str, object], kind: str) -> None:
    body_steps = _colour_names(colours, "body_steps")
    if len(body_steps) > 1:
        _draw_stepped_fill(draw, (0, TOP_BAR_HEIGHT + 4, WIDTH, HEIGHT - BOTTOM_BAR_HEIGHT - 5), body_steps, vertical=True)
        for index, name in enumerate(reversed(body_steps[:4])):
            inset = 10 + index * 10
            draw.rectangle(
                (inset, TOP_BAR_HEIGHT + 12 + index * 8, WIDTH - inset, HEIGHT - BOTTOM_BAR_HEIGHT - 14 - index * 6),
                outline=_rgb(name),
                width=2,
            )
    texture_name = _colour_name(colours, "texture", "white")
    if texture_name == "white":
        return
    texture = _rgb(texture_name)
    if kind == "rain":
        for x in range(-48, WIDTH, 32):
            draw.line((x, TOP_BAR_HEIGHT + 4, x + 78, HEIGHT - BOTTOM_BAR_HEIGHT - 4), fill=texture, width=8)
    else:
        for x in range(0, WIDTH, 14):
            for y in range(TOP_BAR_HEIGHT + 12, HEIGHT - BOTTOM_BAR_HEIGHT - 8, 14):
                draw.point((x, y), fill=texture)
                draw.point((x + 4, y + 5), fill=texture)


def _draw_sun(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, colours: dict[str, object]) -> None:
    outline = _rgb(colours["outline"])
    for angle in range(0, 360, 30):
        x1 = cx + int(math.cos(math.radians(angle)) * (radius + 8))
        y1 = cy + int(math.sin(math.radians(angle)) * (radius + 8))
        x2 = cx + int(math.cos(math.radians(angle)) * (radius + 32))
        y2 = cy + int(math.sin(math.radians(angle)) * (radius + 32))
        draw.line((x1, y1, x2, y2), fill=outline, width=5)
    shades = _colour_names(colours, "symbol_shades") or (_colour_name(colours, "symbol_fill", "bright_yellow"),)
    for index, name in enumerate(shades[:4]):
        inset = index * max(5, radius // 5)
        if inset >= radius:
            break
        draw.ellipse((cx - radius + inset, cy - radius + inset, cx + radius - inset, cy + radius - inset), fill=_rgb(name))
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=outline, width=5)
    accent_name = _colour_name(colours, "symbol_accent", "black")
    if accent_name not in {"black", "white"}:
        draw.ellipse((cx - radius + 15, cy - radius + 15, cx + radius - 15, cy + radius - 15), outline=_rgb(accent_name), width=5)


def _draw_cloud(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    colours: dict[str, object],
    scale: float = 1.0,
    storm: bool = False,
    rain: bool = False,
) -> None:
    outline = _rgb(colours["outline"])
    shades = _colour_names(colours, "symbol_shades")
    fill = _rgb(shades[0] if shades else _colour_name(colours, "symbol_fill", "white"))
    width = max(3, int(5 * scale))

    def ellipse(dx1: int, dy1: int, dx2: int, dy2: int) -> None:
        draw.ellipse(
            (cx + int(dx1 * scale), cy + int(dy1 * scale), cx + int(dx2 * scale), cy + int(dy2 * scale)),
            fill=fill,
            outline=outline,
            width=width,
        )

    ellipse(-92, -4, -30, 58)
    ellipse(-50, -38, 38, 60)
    ellipse(14, -8, 92, 58)
    if len(shades) > 1:
        _draw_stepped_fill(
            draw,
            (cx - int(72 * scale), cy + int(24 * scale), cx + int(72 * scale), cy + int(62 * scale)),
            shades[:4],
        )
    else:
        draw.rectangle((cx - int(72 * scale), cy + int(24 * scale), cx + int(72 * scale), cy + int(62 * scale)), fill=fill)
    draw.line((cx - int(78 * scale), cy + int(62 * scale), cx + int(80 * scale), cy + int(62 * scale)), fill=outline, width=width)
    if rain:
        for dx in (-48, -16, 16, 48):
            draw.line((cx + int(dx * scale), cy + int(76 * scale), cx + int((dx - 13) * scale), cy + int(118 * scale)), fill=outline, width=width)
    if storm:
        points = [
            (cx - 10 * scale, cy + 62 * scale),
            (cx - 44 * scale, cy + 132 * scale),
            (cx - 4 * scale, cy + 110 * scale),
            (cx - 18 * scale, cy + 166 * scale),
            (cx + 42 * scale, cy + 82 * scale),
            (cx + 2 * scale, cy + 104 * scale),
        ]
        int_points = [(int(x), int(y)) for x, y in points]
        draw.polygon(int_points, fill=_rgb(colours["symbol_accent"]), outline=outline)
        draw.line(int_points + [int_points[0]], fill=outline, width=4)


def _draw_moon(draw: ImageDraw.ImageDraw, cx: int, cy: int, colours: dict[str, object]) -> None:
    outline = _rgb(colours["outline"])
    shades = _colour_names(colours, "symbol_shades")
    fill_name = shades[0] if shades else _colour_name(colours, "symbol_fill", "bright_yellow")
    draw.ellipse((cx - 36, cy - 40, cx + 36, cy + 32), fill=_rgb(fill_name), outline=outline, width=4)
    draw.ellipse((cx - 10, cy - 48, cx + 58, cy + 26), fill=_rgb(_colour_name(colours, "symbol_panel", "warm_white")))
    draw.arc((cx - 36, cy - 40, cx + 36, cy + 32), 70, 285, fill=outline, width=5)
    if _colour_name(colours, "symbol_accent", "black") not in {"black", "white"}:
        for sx, sy in ((cx - 44, cy - 46), (cx + 48, cy - 36), (cx + 38, cy + 60)):
            draw.line((sx - 10, sy, sx + 10, sy), fill=_rgb(_colour_name(colours, "symbol_accent", "bright_yellow")), width=4)
            draw.line((sx, sy - 10, sx, sy + 10), fill=_rgb(_colour_name(colours, "symbol_accent", "bright_yellow")), width=4)


def _draw_symbol(draw: ImageDraw.ImageDraw, kind: str, data: WeatherCardData, colours: dict[str, object]) -> None:
    shades = _colour_names(colours, "symbol_shades")
    if len(shades) > 1:
        _draw_stepped_fill(draw, (136, 50, 264, 210), shades, vertical=True)
    else:
        draw.rectangle((136, 50, 264, 210), fill=_rgb(_colour_name(colours, "symbol_panel", "white")))
    if kind == "storm":
        _draw_cloud(draw, 200, 96, colours, scale=0.72, storm=True, rain=True)
    elif kind == "rain":
        _draw_cloud(draw, 200, 88, colours, scale=0.72, rain=True)
    elif kind == "cloud":
        _draw_sun(draw, 178, 105, 33, colours)
        _draw_cloud(draw, 214, 116, colours, scale=0.62)
    elif kind == "night":
        _draw_moon(draw, 198, 116, colours)
    else:
        _draw_sun(draw, 200, 134, 46, colours)

    draw.rectangle((144, 160, 256, 204), fill=_rgb("black"))
    _draw_centred_text(draw, (144, 160, 256, 204), f"{data.temperature}{data.unit}", 56, colours, "inverse_text", True, 32)
    feels_like = f"FEELS LIKE {data.feels_like}" if data.feels_like else "FEELS LIKE --"
    _draw_centred_text(draw, (126, 226, 274, 252), feels_like, 19, colours, "text", True, 11)


def _draw_metric(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    value: str,
    colours: dict[str, object],
    accent: str | None = None,
) -> None:
    accent_names = _colour_names(colours, "metric_accents")
    accent_index = sum(ord(char) for char in label.upper()) % len(accent_names) if accent_names else 0
    accent_name = accent or (accent_names[accent_index] if accent_names else _colour_name(colours, "metric_accent", "bright_yellow"))
    label_width = 32 if label.upper().startswith("PR") else 38
    box_width = 116
    box_height = 36
    draw.rectangle((x, y, x + box_width, y + box_height), fill=_rgb(colours["metric"]), outline=_rgb("black"), width=1)
    draw.rectangle((x, y, x + label_width, y + box_height), fill=_rgb(accent_name))
    draw.line((x + label_width, y, x + label_width, y + box_height), fill=_rgb("black"), width=1)
    label_fill = "inverse_text" if accent_name in {"black", "charcoal", "warm_grey"} else "metric_text"
    _draw_centred_text(draw, (x + 2, y, x + label_width, y + box_height), label[:2].upper(), 22, colours, label_fill, True, 15)
    min_value_size = 14 if label.upper().startswith(("PR", "WI")) else 15
    _draw_centred_text(
        draw,
        (x + label_width + 3, y, x + box_width - 4, y + box_height),
        value,
        23,
        colours,
        "metric_text",
        True,
        min_value_size,
    )


def _detail_value(data: WeatherCardData, labels: tuple[str, ...], fallback: str) -> str:
    details = {label.lower(): value for label, value in data.details}
    for label in labels:
        value = details.get(label.lower())
        if value:
            return value
    return fallback or "--"


def render_weather_card(data: WeatherCardData, colour_mode: str = COLOUR_MODE_COLOUR) -> Image.Image:
    kind = _condition_kind(data.condition, data.alert)
    colours = _colours(kind, colour_mode)

    image = Image.new("RGB", (WIDTH, HEIGHT), _rgb(colours["background"]))
    draw = ImageDraw.Draw(image)

    _draw_texture(draw, colours, kind)
    _draw_bars(draw, data, colours)
    _draw_symbol(draw, kind, data, colours)

    left_details = (
        ("HI", f"{data.high}{data.unit}"),
        ("LO", f"{data.low}{data.unit}"),
        ("UV", _detail_value(data, ("UV", "uv_index"), data.uv_index)),
    )
    right_details = (
        ("HU", _detail_value(data, ("Hum", "Humidity"), data.humidity)),
        ("RA", _detail_value(data, ("Rain",), data.rain)),
        ("WI", _detail_value(data, ("Wind",), data.wind)),
    )
    if kind == "sun":
        left_details = (
            ("UV", _detail_value(data, ("UV", "uv_index"), data.uv_index)),
            ("RA", _detail_value(data, ("Rain",), data.rain)),
            ("PR", data.pressure or "--"),
        )
        right_details = (
            ("HI", f"{data.high}{data.unit}"),
            ("LO", f"{data.low}{data.unit}"),
            ("HU", _detail_value(data, ("Hum", "Humidity"), data.humidity)),
            ("WI", _detail_value(data, ("Wind",), data.wind)),
        )
    if kind == "storm":
        left_details = (("RA", data.rain), ("WI", data.wind), ("UV", data.uv_index or "--"))
        right_details = (("HI", f"{data.high}{data.unit}"), ("LO", f"{data.low}{data.unit}"), ("HU", data.humidity or "--"))
    if kind == "rain":
        left_details = (("RA", data.rain), ("HU", data.humidity or "--"), ("LO", f"{data.low}{data.unit}"))
        right_details = (("HI", f"{data.high}{data.unit}"), ("WI", data.wind), ("PR", data.pressure or "--"))
    if kind == "night":
        left_details = (("LO", f"{data.low}{data.unit}"), ("HU", data.humidity or "--"), ("WI", data.wind))
        right_details = (("HI", f"{data.high}{data.unit}"), ("UV", data.uv_index or "--"), ("PR", data.pressure or "--"))

    if kind == "sun":
        for y, (label, value) in zip((72, 126, 180), left_details):
            _draw_metric(draw, 20, y, label, value, colours, "red" if label in {"UV", "RA"} and not _is_mono(colour_mode) else None)
        for y, (label, value) in zip((58, 100, 142, 184), right_details):
            _draw_metric(draw, 268, y, label, value, colours)
    else:
        for y, (label, value) in zip((58, 105, 152), left_details):
            _draw_metric(draw, 20, y, label, value, colours, "red" if label in {"UV", "RA"} and not _is_mono(colour_mode) else None)
        for y, (label, value) in zip((58, 105, 152), right_details):
            _draw_metric(draw, 268, y, label, value, colours, "red" if label in {"UV", "RA"} and not _is_mono(colour_mode) else None)

    return image
