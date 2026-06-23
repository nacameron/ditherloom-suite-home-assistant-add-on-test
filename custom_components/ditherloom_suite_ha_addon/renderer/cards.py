from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .palette import TEMPLATE_COLOURS

WIDTH = 400
HEIGHT = 300
TOP_BAR_HEIGHT = 38
BOTTOM_BAR_HEIGHT = 38

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


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, size: int, min_size: int, bold: bool = False) -> ImageFont.ImageFont:
    current = size
    while current >= min_size:
        font = _font(current, bold=bold)
        left, top, right, bottom = draw.textbbox((0, 0), str(text), font=font)
        if right - left <= max_width:
            return font
        current -= 1
    return _font(min_size, bold=bold)


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
    font = _fit_text(draw, text, x2 - x1 - 8, size, min_size, bold=bold)
    left, top, right, bottom = draw.textbbox((0, 0), str(text), font=font)
    draw.text(
        (x1 + (x2 - x1 - (right - left)) / 2, y1 + (y2 - y1 - (bottom - top)) / 2 - 1),
        str(text),
        font=font,
        fill=_rgb(colours[fill_name]),
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
    font = _fit_text(draw, text, max_width, size, min_size, bold=bold) if max_width else _font(size, bold=bold)
    draw.text(xy, str(text), font=font, fill=_rgb(colours[fill_name]))


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
    _draw_centred_text(draw, (144, 160, 256, 204), f"{data.temperature}{data.unit}", 40, colours, "inverse_text", True, 24)
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
