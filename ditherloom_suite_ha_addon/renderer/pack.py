from __future__ import annotations

import json
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from PIL import Image

from .palette import RGB_TO_TEMPLATE_NAME, TEMPLATE_COLOURS, codes_to_preview_rgb, nearest_panel_code, ordered_code

WIDTH = 400
HEIGHT = 300
PIXEL_COUNT = WIDTH * HEIGHT
PACKED_LENGTH = PIXEL_COUNT // 4


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


def image_to_codes(image: Image.Image) -> List[int]:
    if image.size != (WIDTH, HEIGHT):
        raise ValueError(f"Expected {WIDTH}x{HEIGHT}, got {image.size[0]}x{image.size[1]}")
    rgb_image = image.convert("RGB")
    pixels = rgb_image.load()
    codes: List[int] = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            rgb = pixels[x, y]
            template_name = RGB_TO_TEMPLATE_NAME.get(rgb)
            if template_name:
                colour = TEMPLATE_COLOURS[template_name]
                if colour.recipe is not None:
                    codes.append(ordered_code(colour.recipe, x, y))
                    continue
                if template_name == "red":
                    codes.append(3)
                    continue
                if template_name == "white":
                    codes.append(1)
                    continue
                codes.append(0)
                continue
            codes.append(nearest_panel_code(rgb))
    return codes


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
    codes = image_to_codes(image)
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
        "crc32": crc32,
        "content_id": content_id,
        "source_entity_ids": source_entity_ids,
        "renderer_version": "prototype-0.1",
        "template_name": template_name,
    }
    return RenderArtifact(
        width=WIDTH,
        height=HEIGHT,
        codes=codes,
        packed=packed,
        crc32=crc32,
        content_id=content_id,
        metadata=metadata,
        preview_image=codes_to_image(codes, PREVIEW_RGB),
        packet_debug_image=codes_to_image(codes, PACKET_RGB),
    )


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

