from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageDraw

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


def _is_mono(colour_mode: str) -> bool:
    return str(colour_mode).lower() in {COLOUR_MODE_MONO, "black_white", "black-and-white", "bw", "b&w"}


def _condition_kind(condition: str, alert: str) -> str:
    normalized = f"{condition} {alert}".lower()
    if "storm" in normalized or "thunder" in normalized:
        return "storm"
    if "rain" in normalized or "shower" in normalized or "drizzle" in normalized:
        return "rain"
    if "night" in normalized:
        return "night"
    if "cloud" in normalized or "overcast" in normalized or "fog" in normalized:
        return "cloud"
    return "sun"


def _colours(kind: str, colour_mode: str) -> dict[str, str]:
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
        }

    if kind == "storm":
        return {
            "background": "paper",
            "texture": "linen",
            "top": "red",
            "top_text": "white",
            "bottom": "red",
            "bottom_text": "white",
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
        }
    if kind == "cloud":
        return {
            "background": "cream",
            "texture": "pale_yellow",
            "top": "black",
            "top_text": "bright_yellow",
            "bottom": "black",
            "bottom_text": "bright_yellow",
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
        }
    if kind == "night":
        return {
            "background": "black",
            "texture": "charcoal",
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
    }


def _draw_bars(draw: ImageDraw.ImageDraw, data: WeatherCardData, colours: dict[str, str]) -> None:
    draw.rectangle((0, 0, WIDTH, TOP_BAR_HEIGHT), fill=_rgb(colours["top"]))
    draw.rectangle((0, HEIGHT - BOTTOM_BAR_HEIGHT, WIDTH, HEIGHT), fill=_rgb(colours["bottom"]))
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


def _draw_texture(draw: ImageDraw.ImageDraw, colours: dict[str, str], kind: str) -> None:
    if _is_mono(colours["texture"]):
        return
    texture = _rgb(colours["texture"])
    if kind == "rain":
        for x in range(-48, WIDTH, 32):
            draw.line((x, TOP_BAR_HEIGHT + 4, x + 78, HEIGHT - BOTTOM_BAR_HEIGHT - 4), fill=texture, width=8)
    else:
        for x in range(0, WIDTH, 14):
            for y in range(TOP_BAR_HEIGHT + 12, HEIGHT - BOTTOM_BAR_HEIGHT - 8, 14):
                draw.point((x, y), fill=texture)
                draw.point((x + 4, y + 5), fill=texture)


def _draw_sun(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, colours: dict[str, str]) -> None:
    outline = _rgb(colours["outline"])
    for angle in range(0, 360, 30):
        x1 = cx + int(math.cos(math.radians(angle)) * (radius + 8))
        y1 = cy + int(math.sin(math.radians(angle)) * (radius + 8))
        x2 = cx + int(math.cos(math.radians(angle)) * (radius + 32))
        y2 = cy + int(math.sin(math.radians(angle)) * (radius + 32))
        draw.line((x1, y1, x2, y2), fill=outline, width=5)
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=_rgb(colours["symbol_fill"]), outline=outline, width=5)
    if not _is_mono(colours["symbol_accent"]):
        draw.ellipse((cx - radius + 15, cy - radius + 15, cx + radius - 15, cy + radius - 15), outline=_rgb(colours["symbol_accent"]), width=5)


def _draw_cloud(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    colours: dict[str, str],
    scale: float = 1.0,
    storm: bool = False,
    rain: bool = False,
) -> None:
    outline = _rgb(colours["outline"])
    fill = _rgb(colours["symbol_fill"])
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


def _draw_moon(draw: ImageDraw.ImageDraw, cx: int, cy: int, colours: dict[str, str]) -> None:
    outline = _rgb(colours["outline"])
    draw.ellipse((cx - 36, cy - 40, cx + 36, cy + 32), fill=_rgb(colours["symbol_fill"]), outline=outline, width=4)
    draw.ellipse((cx - 10, cy - 48, cx + 58, cy + 26), fill=_rgb(colours["symbol_panel"]))
    draw.arc((cx - 36, cy - 40, cx + 36, cy + 32), 70, 285, fill=outline, width=5)
    if not _is_mono(colours["symbol_accent"]):
        for sx, sy in ((cx - 44, cy - 46), (cx + 48, cy - 36), (cx + 38, cy + 60)):
            draw.line((sx - 10, sy, sx + 10, sy), fill=_rgb(colours["symbol_accent"]), width=4)
            draw.line((sx, sy - 10, sx, sy + 10), fill=_rgb(colours["symbol_accent"]), width=4)


def _draw_symbol(draw: ImageDraw.ImageDraw, kind: str, data: WeatherCardData, colours: dict[str, str]) -> None:
    draw.rectangle((136, 50, 264, 210), fill=_rgb(colours["symbol_panel"]), outline=_rgb("black"), width=5)
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
    colours: dict[str, str],
    accent: str | None = None,
) -> None:
    accent_name = accent or colours["metric_accent"]
    draw.rectangle((x, y, x + 112, y + 34), fill=_rgb(colours["metric"]), outline=_rgb("black"), width=3)
    draw.rectangle((x, y, x + 30, y + 34), fill=_rgb(accent_name))
    draw.line((x + 30, y, x + 30, y + 34), fill=_rgb("black"), width=3)
    label_fill = "inverse_text" if accent_name in {"black", "charcoal", "warm_grey"} else "metric_text"
    _draw_centred_text(draw, (x + 2, y, x + 30, y + 34), label[:2].upper(), 14, colours, label_fill, True, 9)
    _draw_centred_text(draw, (x + 34, y, x + 108, y + 34), value, 18, colours, "metric_text", True, 10)


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
