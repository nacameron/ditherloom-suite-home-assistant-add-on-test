from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .palette import TEMPLATE_COLOURS

WIDTH = 400
HEIGHT = 300


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
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, size: int, min_size: int, bold: bool = False) -> ImageFont.ImageFont:
    current = size
    while current > min_size:
        font = _font(current, bold=bold)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        if right - left <= max_width:
            return font
        current -= 2
    return _font(min_size, bold=bold)


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont, fill_name: str = "black") -> None:
    draw.text(xy, text, font=font, fill=TEMPLATE_COLOURS[fill_name].rgb)


def _draw_sun(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int = 29) -> None:
    yellow = TEMPLATE_COLOURS["bright_yellow"].rgb
    black = TEMPLATE_COLOURS["black"].rgb
    for angle in range(0, 360, 45):
        import math

        x1 = cx + int(math.cos(math.radians(angle)) * (radius + 8))
        y1 = cy + int(math.sin(math.radians(angle)) * (radius + 8))
        x2 = cx + int(math.cos(math.radians(angle)) * (radius + 24))
        y2 = cy + int(math.sin(math.radians(angle)) * (radius + 24))
        draw.line((x1, y1, x2, y2), fill=black, width=3)
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=yellow, outline=black, width=3)


def _draw_cloud(draw: ImageDraw.ImageDraw, x: int, y: int, storm: bool = False) -> None:
    white = TEMPLATE_COLOURS["white"].rgb
    black = TEMPLATE_COLOURS["black"].rgb
    yellow = TEMPLATE_COLOURS["bright_yellow"].rgb
    draw.ellipse((x + 12, y + 24, x + 66, y + 74), fill=white, outline=black, width=3)
    draw.ellipse((x + 48, y + 10, x + 112, y + 76), fill=white, outline=black, width=3)
    draw.ellipse((x + 96, y + 26, x + 150, y + 74), fill=white, outline=black, width=3)
    draw.rectangle((x + 31, y + 48, x + 132, y + 78), fill=white)
    draw.line((x + 22, y + 77, x + 138, y + 77), fill=black, width=3)
    if storm:
        draw.polygon((x + 70, y + 78, x + 52, y + 128, x + 82, y + 112, x + 70, y + 154, x + 112, y + 94, x + 82, y + 108), fill=yellow, outline=black)


def _draw_weather_scene(draw: ImageDraw.ImageDraw, condition: str, alert: str) -> None:
    black = TEMPLATE_COLOURS["black"].rgb
    white = TEMPLATE_COLOURS["white"].rgb
    yellow = TEMPLATE_COLOURS["bright_yellow"].rgb
    parchment = TEMPLATE_COLOURS["parchment"].rgb
    pale_cream = TEMPLATE_COLOURS["pale_cream"].rgb
    red = TEMPLATE_COLOURS["red"].rgb

    normalized = condition.lower()
    storm = "storm" in normalized or "thunder" in normalized
    rain = "rain" in normalized or "shower" in normalized
    cloud = storm or rain or "cloud" in normalized or "overcast" in normalized

    draw.rectangle((12, 14, 170, 224), fill=white, outline=black, width=5)
    draw.rectangle((18, 20, 164, 116), fill=yellow)
    draw.rectangle((18, 116, 164, 218), fill=parchment)
    draw.line((18, 116, 164, 116), fill=black, width=4)

    if cloud:
        draw.ellipse((104, 28, 170, 94), fill=yellow, outline=black, width=4)
        draw.ellipse((24, 76, 94, 146), fill=white, outline=black, width=5)
        draw.ellipse((66, 48, 150, 148), fill=white, outline=black, width=5)
        draw.ellipse((120, 82, 178, 146), fill=white, outline=black, width=5)
        draw.rectangle((42, 108, 158, 150), fill=white)
        draw.line((30, 149, 160, 149), fill=black, width=5)
        if storm:
            draw.polygon((98, 148, 72, 214, 110, 188, 96, 230, 148, 160, 112, 182), fill=yellow, outline=black)
            draw.rectangle((24, 28, 58, 62), fill=red, outline=black, width=3)
        elif rain:
            for x in (56, 86, 116, 146):
                draw.line((x, 158, x - 14, 204), fill=black, width=5)
                draw.line((x + 8, 158, x - 6, 204), fill=yellow, width=4)
    else:
        _draw_sun(draw, 94, 92, radius=52)

    draw.polygon((18, 218, 18, 166, 58, 138, 94, 176, 128, 140, 164, 170, 164, 218), fill=white, outline=black)
    draw.arc((32, 138, 140, 248), 200, 340, fill=black, width=5)
    draw.rectangle((18, 198, 164, 218), fill=yellow if not alert.strip() else red)


def _draw_weather_icon(draw: ImageDraw.ImageDraw, condition: str) -> None:
    normalized = condition.lower()
    if "storm" in normalized or "thunder" in normalized:
        _draw_cloud(draw, 28, 48, storm=True)
    elif "cloud" in normalized or "rain" in normalized or "shower" in normalized:
        _draw_cloud(draw, 28, 62, storm=False)
        if "rain" in normalized or "shower" in normalized:
            black = TEMPLATE_COLOURS["black"].rgb
            for x in (62, 92, 122):
                draw.line((x, 148, x - 8, 170), fill=black, width=3)
    else:
        _draw_sun(draw, 96, 104)


def render_weather_card(data: WeatherCardData) -> Image.Image:
    white = TEMPLATE_COLOURS["white"].rgb
    warm_white = TEMPLATE_COLOURS["warm_white"].rgb
    parchment = TEMPLATE_COLOURS["parchment"].rgb
    yellow = TEMPLATE_COLOURS["bright_yellow"].rgb
    red = TEMPLATE_COLOURS["red"].rgb
    black = TEMPLATE_COLOURS["black"].rgb
    warm_grey = TEMPLATE_COLOURS["warm_grey"].rgb

    image = Image.new("RGB", (WIDTH, HEIGHT), white)
    draw = ImageDraw.Draw(image)

    # Warm left panel gives the card colour without making text noisy.
    draw.rectangle((0, 0, 184, HEIGHT), fill=warm_white)
    draw.rectangle((184, 0, 192, HEIGHT), fill=yellow)
    if not data.alert.strip():
        draw.rectangle((192, 0, WIDTH, 12), fill=yellow)
    _draw_weather_scene(draw, data.condition, data.alert)

    if data.alert.strip():
        draw.rectangle((0, 0, WIDTH, 38), fill=red)
        alert_font = _fit_text(draw, data.alert.strip().upper(), 370, 22, 16, bold=True)
        _text(draw, (16, 7), data.alert.strip().upper(), alert_font, "white")

    title_y = 48 if data.alert.strip() else 20
    title_font = _fit_text(draw, data.location, 180, 30, 20, bold=True)
    _text(draw, (208, title_y), data.location, title_font)

    temp_label = f"{data.temperature}{data.unit}"
    temp_font = _fit_text(draw, temp_label, 174, 78, 52, bold=True)
    _text(draw, (208, title_y + 34), temp_label, temp_font)

    condition_font = _fit_text(draw, data.condition, 174, 28, 18, bold=True)
    _text(draw, (210, title_y + 118), data.condition, condition_font)

    draw.rectangle((208, 202, 382, 206), fill=warm_grey)
    detail_font = _font(19, bold=True)
    label_font = _font(14, bold=True)
    details = data.details or (
        ("High", f"{data.high}{data.unit}"),
        ("Low", f"{data.low}{data.unit}"),
        ("Hum", data.humidity or "--"),
        ("UV", data.uv_index or "--"),
        ("Rain", data.rain),
        ("Wind", data.wind),
    )
    slots = ((210, 219), (300, 219), (210, 247), (300, 247), (210, 275), (300, 275))
    for (label, value), (x, y) in zip(details[:6], slots):
        short_label = label[:5]
        _text(draw, (x, y), short_label, label_font)
        fitted = _fit_text(draw, value, 48, 19, 13, bold=True)
        _text(draw, (x + 41, y - 2), value, fitted)

    footer_font = _font(15)
    _text(draw, (18, 260), f"Updated {data.updated}", footer_font)
    return image
