from __future__ import annotations

import json
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from PIL import Image

from ..const import (
    DEVICE_FRAME_HEIGHT,
    DEVICE_FRAME_WIDTH,
    DEVICE_PACKED_PAYLOAD_BYTES,
    DEVICE_PIXEL_COUNT,
    DEVICE_SLOT_STRIDE_BYTES,
    DEVICE_SOURCE_METADATA_HEADER_BYTES,
    DEVICE_SOURCE_METADATA_PAYLOAD_BYTES,
)
from .palette import CODE_BLACK, CODE_RED, CODE_WHITE, CODE_YELLOW, PACKET_RGB, RGB_TO_TEMPLATE_NAME, TEMPLATE_COLOURS, ordered_code

WIDTH = DEVICE_FRAME_WIDTH
HEIGHT = DEVICE_FRAME_HEIGHT
PIXEL_COUNT = DEVICE_PIXEL_COUNT
PACKED_LENGTH = DEVICE_PACKED_PAYLOAD_BYTES
DEVICE_ORIENTATION_TRANSFORM = "flip_vertical_per_device_packet_spec"
ATKINSON_KERNEL = (
    (1, 0, 1 / 8),
    (2, 0, 1 / 8),
    (-1, 1, 1 / 8),
    (0, 1, 1 / 8),
    (1, 1, 1 / 8),
    (0, 2, 1 / 8),
)
TEMPLATE_RECIPE_MATCH_DISTANCE_SQUARED = 0


@dataclass(frozen=True)
class RenderArtifact:
    width: int
    height: int
    codes: List[int]
    packed: bytes
    crc32: str
    content_id: str
    metadata: Dict[str, object]
    preview_image: Image.Image
    packet_debug_image: Image.Image


def image_to_codes(image: Image.Image, protected_mask: Image.Image | None = None) -> List[int]:
    if image.size != (WIDTH, HEIGHT):
        raise ValueError(f"Expected {WIDTH}x{HEIGHT}, got {image.size[0]}x{image.size[1]}")
    rgb_image = image.convert("RGB")
    mask_pixels = None
    if protected_mask is not None:
        if protected_mask.size != (WIDTH, HEIGHT):
            raise ValueError(
                f"Expected protected mask {WIDTH}x{HEIGHT}, got {protected_mask.size[0]}x{protected_mask.size[1]}"
            )
        mask_pixels = protected_mask.convert("L").load()
    pixels = [
        [[float(channel) for channel in rgb_image.getpixel((x, y))] for x in range(WIDTH)]
        for y in range(HEIGHT)
    ]
    source_pixels = rgb_image.load()
    codes: List[int] = [0] * PIXEL_COUNT
    for y in range(HEIGHT):
        for x in range(WIDTH):
            rgb = source_pixels[x, y]
            if mask_pixels is None or mask_pixels[x, y] > 0:
                template_code = _template_safe_palette_code(rgb, x, y)
                if template_code is not None:
                    codes[y * WIDTH + x] = template_code
                    continue

            r, g, b = pixels[y][x]
            code, nr, ng, nb = closest_panel_code_and_rgb(r, g, b)
            codes[y * WIDTH + x] = code
            diffuse_photo_error(pixels, x, y, (r - nr, g - ng, b - nb))
    return codes


def _template_safe_palette_code(rgb: tuple[int, int, int], x: int, y: int) -> int | None:
    template_name = RGB_TO_TEMPLATE_NAME.get(rgb)
    if template_name in {"black", "red", "yellow", "bright_yellow", "white"}:
        return _template_colour_code(TEMPLATE_COLOURS[template_name].rgb, x, y)
    return None


def _template_colour_code(rgb: tuple[int, int, int], x: int, y: int) -> int:
    colour_name = RGB_TO_TEMPLATE_NAME.get(rgb)
    if colour_name is None:
        return closest_panel_code_and_rgb(*rgb)[0]
    if colour_name == "black":
        return CODE_BLACK
    if colour_name == "red":
        return CODE_RED
    if colour_name in {"yellow", "bright_yellow"}:
        return CODE_YELLOW
    if colour_name == "white":
        return CODE_WHITE
    colour = TEMPLATE_COLOURS[colour_name]
    if colour.recipe is not None:
        return ordered_code(colour.recipe, x, y)
    return CODE_BLACK


def closest_panel_code_and_rgb(r: float, g: float, b: float) -> tuple[int, int, int, int]:
    best_code = 0
    best_rgb = PACKET_RGB[0]
    best_error = float("inf")
    for code, (pr, pg, pb) in PACKET_RGB.items():
        error = abs(r - pr) + abs(g - pg) + abs(b - pb)
        if error < best_error:
            best_code = code
            best_rgb = (pr, pg, pb)
            best_error = error
    return best_code, best_rgb[0], best_rgb[1], best_rgb[2]


def diffuse_photo_error(
    pixels: list[list[list[float]]],
    x: int,
    y: int,
    error: tuple[float, float, float],
) -> None:
    er, eg, eb = error
    for dx, dy, weight in ATKINSON_KERNEL:
        xx = x + dx
        yy = y + dy
        if 0 <= xx < WIDTH and 0 <= yy < HEIGHT:
            pixels[yy][xx][0] += er * weight
            pixels[yy][xx][1] += eg * weight
            pixels[yy][xx][2] += eb * weight


def pack_pixel_codes(codes: List[int]) -> bytes:
    packed = bytearray((len(codes) + 3) // 4)
    for n in range(0, len(codes), 4):
        value = 0
        for i in range(4):
            if n + i < len(codes):
                value |= (codes[n + i] & 0x03) << (6 - 2 * i)
        packed[n // 4] = value
    return bytes(packed)


def codes_to_image(codes: List[int], palette: Dict[int, tuple[int, int, int]]) -> Image.Image:
    if len(codes) != PIXEL_COUNT:
        raise ValueError(f"Expected {PIXEL_COUNT} pixel codes, got {len(codes)}")
    image = Image.new("RGB", (WIDTH, HEIGHT))
    image.putdata([palette[int(code)] for code in codes])
    return image


def render_to_artifact(image: Image.Image, template_name: str, source_entity_ids: list[str]) -> RenderArtifact:
    oriented_image = orient_image_for_device(image)
    protected_mask = image.info.get("ditherloom_protected_mask")
    oriented_mask = orient_image_for_device(protected_mask) if isinstance(protected_mask, Image.Image) else None
    codes = image_to_codes(oriented_image, oriented_mask)
    packed = pack_pixel_codes(codes)
    if len(codes) != PIXEL_COUNT:
        raise ValueError(f"Expected {PIXEL_COUNT} pixel codes, got {len(codes)}")
    if len(packed) != PACKED_LENGTH:
        raise ValueError(f"Expected {PACKED_LENGTH} packed bytes, got {len(packed)}")
    crc32 = f"{zlib.crc32(packed) & 0xFFFFFFFF:08X}"
    content_id = f"{template_name}-{crc32.lower()}"
    from .palette import PACKET_RGB, PREVIEW_RGB

    metadata: Dict[str, object] = {
        "width": WIDTH,
        "height": HEIGHT,
        "packed_length": len(packed),
        "slot_stride_bytes": DEVICE_SLOT_STRIDE_BYTES,
        "source_metadata_header_bytes": DEVICE_SOURCE_METADATA_HEADER_BYTES,
        "source_metadata_payload_bytes": DEVICE_SOURCE_METADATA_PAYLOAD_BYTES,
        "crc32": crc32,
        "content_id": content_id,
        "source_entity_ids": source_entity_ids,
        "renderer_version": "prototype-0.1",
        "template_name": template_name,
        "device_orientation_transform": DEVICE_ORIENTATION_TRANSFORM,
    }
    raw_preview = codes_to_image(codes, PREVIEW_RGB)
    raw_packet_debug = codes_to_image(codes, PACKET_RGB)
    return RenderArtifact(
        width=WIDTH,
        height=HEIGHT,
        codes=codes,
        packed=packed,
        crc32=crc32,
        content_id=content_id,
        metadata=metadata,
        preview_image=orient_preview_for_viewer(raw_preview),
        packet_debug_image=orient_preview_for_viewer(raw_packet_debug),
    )


def orient_image_for_device(image: Image.Image) -> Image.Image:
    if image.size != (WIDTH, HEIGHT):
        raise ValueError(f"Expected {WIDTH}x{HEIGHT}, got {image.size[0]}x{image.size[1]}")
    return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)


def orient_preview_for_viewer(image: Image.Image) -> Image.Image:
    return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)


def write_artifact(artifact: RenderArtifact, output_dir: Path, stem: str) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ppbin_path = output_dir / f"{stem}.ppbin"
    preview_path = output_dir / f"{stem}.preview.png"
    debug_path = output_dir / f"{stem}.packet.png"
    metadata_path = output_dir / f"{stem}.json"

    ppbin_path.write_bytes(artifact.packed)
    artifact.preview_image.save(preview_path)
    artifact.packet_debug_image.save(debug_path)
    metadata_path.write_text(json.dumps(artifact.metadata, indent=2), encoding="utf-8")
    return {
        "ppbin": ppbin_path,
        "preview": preview_path,
        "packet_debug": debug_path,
        "metadata": metadata_path,
    }
