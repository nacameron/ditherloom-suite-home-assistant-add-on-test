from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

RGB = Tuple[int, int, int]
Recipe = Tuple[float, float, float, float]

CODE_BLACK = 0
CODE_WHITE = 1
CODE_YELLOW = 2
CODE_RED = 3

PACKET_RGB: Dict[int, RGB] = {
    CODE_BLACK: (0, 0, 0),
    CODE_WHITE: (255, 255, 255),
    CODE_YELLOW: (255, 255, 0),
    CODE_RED: (255, 0, 0),
}

PREVIEW_RGB: Dict[int, RGB] = {
    CODE_BLACK: (18, 20, 18),
    CODE_WHITE: (205, 206, 198),
    CODE_YELLOW: (202, 174, 62),
    CODE_RED: (164, 63, 55),
}


@dataclass(frozen=True)
class TemplateColour:
    name: str
    rgb: RGB
    recipe: Recipe | None


TEMPLATE_COLOURS: Dict[str, TemplateColour] = {
    "black": TemplateColour("black", (17, 17, 17), None),
    "charcoal": TemplateColour("charcoal", (51, 51, 51), (0.0, 0.0, 0.16, 0.84)),
    "white": TemplateColour("white", (255, 255, 255), None),
    "warm_white": TemplateColour("warm_white", (255, 248, 232), (0.0, 0.02, 0.98, 0.0)),
    "cream": TemplateColour("cream", (255, 237, 190), (0.0, 0.14, 0.86, 0.0)),
    "pale_cream": TemplateColour("pale_cream", (244, 230, 200), (0.0, 0.09, 0.91, 0.0)),
    "paper": TemplateColour("paper", (225, 221, 209), (0.0, 0.0, 0.96, 0.04)),
    "linen": TemplateColour("linen", (185, 176, 160), (0.0, 0.0, 0.90, 0.10)),
    "warm_grey": TemplateColour("warm_grey", (85, 80, 73), (0.0, 0.0, 0.36, 0.64)),
    "yellow": TemplateColour("yellow", (244, 176, 0), (0.0, 0.70, 0.30, 0.0)),
    "bright_yellow": TemplateColour("bright_yellow", (255, 217, 40), (0.0, 0.90, 0.10, 0.0)),
    "pale_yellow": TemplateColour("pale_yellow", (255, 244, 169), (0.0, 0.22, 0.78, 0.0)),
    "gold": TemplateColour("gold", (217, 145, 0), (0.14, 0.72, 0.0, 0.14)),
    "dark_gold": TemplateColour("dark_gold", (165, 111, 0), (0.08, 0.68, 0.0, 0.24)),
    "red": TemplateColour("red", (209, 25, 32), None),
    "warm_red": TemplateColour("warm_red", (196, 74, 92), (0.62, 0.0, 0.18, 0.20)),
    "dark_red": TemplateColour("dark_red", (155, 17, 30), (0.66, 0.0, 0.0, 0.34)),
    "burgundy": TemplateColour("burgundy", (110, 31, 53), (0.42, 0.0, 0.0, 0.58)),
    "deep_burgundy": TemplateColour("deep_burgundy", (80, 26, 36), (0.28, 0.0, 0.0, 0.72)),
    "blush": TemplateColour("blush", (255, 226, 226), (0.12, 0.0, 0.88, 0.0)),
    "peach": TemplateColour("peach", (255, 208, 176), (0.10, 0.16, 0.74, 0.0)),
    "rose": TemplateColour("rose", (242, 163, 163), (0.22, 0.0, 0.78, 0.0)),
    "orange": TemplateColour("orange", (230, 106, 26), (0.50, 0.50, 0.0, 0.0)),
    "burnt_orange": TemplateColour("burnt_orange", (200, 74, 27), (0.24, 0.66, 0.0, 0.10)),
    "terracotta": TemplateColour("terracotta", (182, 90, 60), (0.42, 0.28, 0.0, 0.30)),
    "brown": TemplateColour("brown", (140, 90, 43), (0.20, 0.24, 0.0, 0.56)),
    "dark_brown": TemplateColour("dark_brown", (74, 46, 29), (0.12, 0.12, 0.0, 0.76)),
    "tan": TemplateColour("tan", (215, 179, 122), (0.04, 0.30, 0.56, 0.10)),
    "parchment": TemplateColour("parchment", (247, 222, 179), (0.0, 0.04, 0.94, 0.02)),
    "maroon": TemplateColour("maroon", (185, 45, 52), (0.60, 0.05, 0.0, 0.35)),
}

RGB_TO_TEMPLATE_NAME = {colour.rgb: name for name, colour in TEMPLATE_COLOURS.items()}

BAYER_8X8 = (
    (0, 48, 12, 60, 3, 51, 15, 63),
    (32, 16, 44, 28, 35, 19, 47, 31),
    (8, 56, 4, 52, 11, 59, 7, 55),
    (40, 24, 36, 20, 43, 27, 39, 23),
    (2, 50, 14, 62, 1, 49, 13, 61),
    (34, 18, 46, 30, 33, 17, 45, 29),
    (10, 58, 6, 54, 9, 57, 5, 53),
    (42, 26, 38, 22, 41, 25, 37, 21),
)


def ordered_code(recipe: Recipe, x: int, y: int) -> int:
    threshold = (BAYER_8X8[y % 8][x % 8] + 0.5) / 64.0
    red, yellow, white, black = recipe
    if threshold < red:
        return CODE_RED
    if threshold < red + yellow:
        return CODE_YELLOW
    if threshold < red + yellow + white:
        return CODE_WHITE
    if threshold < red + yellow + white + black:
        return CODE_BLACK
    return CODE_WHITE


def nearest_panel_code(rgb: RGB) -> int:
    r, g, b = rgb
    if r < 80 and g < 80 and b < 80:
        return CODE_BLACK
    if r > 150 and g < 95 and b < 95:
        return CODE_RED
    if r > 150 and g > 120 and b < 100:
        return CODE_YELLOW
    distances = {
        code: (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        for code, (pr, pg, pb) in PACKET_RGB.items()
    }
    return min(distances, key=distances.get)


def codes_to_preview_rgb(codes: Iterable[int]) -> list[RGB]:
    return [PREVIEW_RGB[int(code)] for code in codes]

