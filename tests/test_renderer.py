from PIL import Image, ImageDraw

from renderer.cards import WeatherCardData, render_modern_weather_card, render_weather_card
from renderer.palette import PREVIEW_RGB, TEMPLATE_COLOURS
from renderer.pack import HEIGHT, PACKED_LENGTH, WIDTH, image_to_codes, pack_pixel_codes, render_to_artifact


def test_blank_white_packs_to_expected_length_and_value():
    image = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    artifact = render_to_artifact(image, "blank_white", [])

    assert len(artifact.codes) == WIDTH * HEIGHT
    assert len(artifact.packed) == PACKED_LENGTH
    assert set(artifact.packed) == {0x55}
    assert artifact.metadata["packed_length"] == PACKED_LENGTH


def test_blank_black_packs_to_zero_bytes():
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    artifact = render_to_artifact(image, "blank_black", [])

    assert len(artifact.packed) == PACKED_LENGTH
    assert set(artifact.packed) == {0x00}


def test_pack_pixel_codes_bit_order():
    packed = pack_pixel_codes([0, 1, 2, 3])

    assert packed == bytes([0b00011011])


def test_weather_card_uses_multiple_panel_colours():
    image = render_weather_card(
        WeatherCardData(
            location="Kitchen",
            condition="Storm",
            temperature="31",
            high="34",
            low="22",
            rain="80%",
            wind="28 km/h",
            alert="Severe storm",
        )
    )
    codes = image_to_codes(image)

    assert image.size == (WIDTH, HEIGHT)
    assert {0, 1, 2, 3}.issubset(set(codes))


def test_modern_weather_card_uses_luxe_hq_layout():
    image = render_modern_weather_card(
        WeatherCardData(
            location="Sydney",
            condition="Partly cloudy",
            temperature="22",
            high="24",
            low="16",
            rain="40%",
            wind="18 km/h",
            updated="5:18 PM",
            humidity="76%",
            uv_index="5.6",
            feels_like="20°C",
        )
    )

    assert image.size == (WIDTH, HEIGHT)
    artifact = render_to_artifact(image, "modern_weather_card", [])
    assert len(artifact.packed) == PACKED_LENGTH
    assert artifact.metadata["packed_length"] == PACKED_LENGTH
    assert len(set(image.getdata())) > 30


def test_modern_weather_card_temperature_renders_with_large_panel_text():
    image = render_modern_weather_card(
        WeatherCardData(
            location="Wollstonecraft",
            condition="Cloudy",
            temperature="17",
            high="21",
            low="14",
            rain="100%",
            wind="17 km/h",
            updated="00:45",
            humidity="78%",
            uv_index="3.5",
            feels_like="15C",
            attribution="Weather data by Open-Meteo.com.",
        )
    )
    pixels = image.load()
    black_points = [
        (x, y)
        for y in range(199, 247)
        for x in range(28, 158)
        if pixels[x, y] == TEMPLATE_COLOURS["black"].rgb
    ]

    assert black_points
    min_x = min(x for x, _ in black_points)
    max_x = max(x for x, _ in black_points)
    min_y = min(y for _, y in black_points)
    max_y = max(y for _, y in black_points)
    assert max_x - min_x >= 58
    assert max_y - min_y >= 29


def test_hybrid_template_colours_are_protected_from_photo_dither():
    image = Image.new("RGB", (WIDTH, HEIGHT), TEMPLATE_COLOURS["warm_white"].rgb)
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 119, 59), fill=TEMPLATE_COLOURS["black"].rgb)
    draw.rectangle((20, 70, 119, 109), fill=TEMPLATE_COLOURS["red"].rgb)
    artifact = render_to_artifact(image, "hybrid_template_guard", [])

    assert len(artifact.packed) == PACKED_LENGTH
    assert set(artifact.codes).issubset({0, 1, 2, 3})
    assert _display_code(artifact.codes, 25, 25) == 0
    assert _display_code(artifact.codes, 25, 75) == 3

    panel_codes = {
        _display_code(artifact.codes, x, y)
        for x in range(180, 220)
        for y in range(130, 170)
    }
    assert panel_codes.issubset({1, 2})
    assert 0 not in panel_codes
    assert 3 not in panel_codes


def test_exact_panel_colours_are_not_dithered():
    image = Image.new("RGB", (WIDTH, HEIGHT), TEMPLATE_COLOURS["white"].rgb)
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 29, 29), fill=TEMPLATE_COLOURS["black"].rgb)
    draw.rectangle((40, 10, 59, 29), fill=TEMPLATE_COLOURS["red"].rgb)
    draw.rectangle((70, 10, 89, 29), fill=TEMPLATE_COLOURS["yellow"].rgb)
    codes = image_to_codes(image)

    assert {codes[y * WIDTH + x] for x in range(10, 30) for y in range(10, 30)} == {0}
    assert {codes[y * WIDTH + x] for x in range(40, 60) for y in range(10, 30)} == {3}
    assert {codes[y * WIDTH + x] for x in range(70, 90) for y in range(10, 30)} == {2}


def test_hybrid_preview_uses_display_palette():
    image = Image.new("RGB", (WIDTH, HEIGHT), TEMPLATE_COLOURS["white"].rgb)
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 30, 30), fill=TEMPLATE_COLOURS["black"].rgb)
    draw.rectangle((40, 10, 60, 30), fill=TEMPLATE_COLOURS["red"].rgb)
    artifact = render_to_artifact(image, "hybrid_preview_palette", [])

    assert artifact.preview_image.getpixel((15, 15)) == PREVIEW_RGB[0]
    assert artifact.preview_image.getpixel((45, 15)) == PREVIEW_RGB[3]


def _display_code(codes: list[int], x: int, y: int) -> int:
    return codes[y * WIDTH + x]
