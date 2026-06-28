# Provider 02: Moon Phase

## Status

Implemented with phase-aware artwork selection.

All eight moon phase images are installed in:

- `custom_components/ditherloom_suite_ha_addon/assets/moon_art/`
- `renderer/assets/moon_art/`

The renderer also keeps a generic fallback:

- `moon_phase_background.png`

## Firmware Commands

No new firmware commands are required.

Moon Phase renders the same 400x300 packed `.ppbin` payload as the weather and
sun providers. Delivery reuses the existing Wi-Fi Gateway command path:

- `PING`
- `BEGIN`
- `B64WRITE`
- `END`
- `DISPLAY`
- `IDLE`

## Phase Artwork

The artwork follows the actual lunar phase using these files:

1. `moon_new_background.png`
2. `moon_waxing_crescent_background.png`
3. `moon_first_quarter_background.png`
4. `moon_waxing_gibbous_background.png`
5. `moon_full_background.png`
6. `moon_waning_gibbous_background.png`
7. `moon_last_quarter_background.png`
8. `moon_waning_crescent_background.png`

Each file should be `400x300`, flat PNG, no transparency.

## Shared Image Rules

- Do not include text, numbers, icons, UI panels, borders, logos, or a frame mockup.
- Source images must remain untouched.
- The renderer applies the standard supplied-HQ-image treatment at render time:
  - saturation `1.2`
  - contrast `1.15`
- The image is then dithered by the existing packer.
- Do not globally snap supplied HQ artwork to the nearest safe colour.
- Keep the moon/phase form visible after dithering.
- Avoid a full black sky. The device does not light up, so large dark areas can
  become heavy and hard to read.

## ChatGPT Prompt Template

Replace `{PHASE_NAME}` and `{PHASE_DESCRIPTION}` for each phase.

```text
Create one 400x300 PNG background image for a Ditherloom e-ink Moon Phase Home Assistant card.

Lunar phase: {PHASE_NAME}
Phase appearance: {PHASE_DESCRIPTION}

The image should show a large clear moon over a calm warm night or twilight sky, with a subtle horizon, sea, or soft clouds. It must feel quiet, premium, and readable on a small e-ink display.

No text, no numbers, no icons, no UI panels, no border, no logo, no frame mockup.

The device is a small four-colour e-ink panel and does not light up. Do not make the image too dark. Use dark tones only for sky depth, cloud definition, and small silhouette detail. Keep enough light areas so black text and small UI panels can remain readable.

The final app will apply a render-time saturation boost of 20% and contrast boost of 15%, then dither the image. Do not snap the artwork to nearest colours.

Use this Ditherloom 30-colour sheet as the intended palette direction:
black #111111
charcoal #333333
white #FFFFFF
warm_white #FFF8E8
cream #FFEDBE
pale_cream #F4E6C8
paper #E1DDD1
linen #B9B0A0
warm_grey #555049
yellow #F4B000
bright_yellow #FFD928
pale_yellow #FFF4A9
gold #D99100
dark_gold #A56F00
red #D11920
warm_red #C44A5C
dark_red #9B111E
burgundy #6E1F35
deep_burgundy #501A24
blush #FFE2E2
peach #FFD0B0
rose #F2A3A3
orange #E66A1A
burnt_orange #C84A1B
terracotta #B65A3C
brown #8C5A2B
dark_brown #4A2E1D
tan #D7B37A
parchment #F7DEB3
maroon #B92D34

Preferred balance: paper, linen, warm_white, pale_cream, parchment, warm_grey, charcoal, pale_yellow, gold. Use black sparingly. Avoid a full black sky.

Composition: place the moon large and clearly visible in the upper half of the image, ideally upper-middle or center-right. Leave calmer lower space for overlay data. Broad simple shapes, no tiny stars or dense texture.

Output: flat PNG, 400x300, no transparency.
```

## Phase Prompt Values

- New Moon: a mostly dark moon silhouette with a very subtle rim light, not a blank black circle.
- Waxing Crescent: a slim bright crescent lit on the right side.
- First Quarter: right half of the moon bright, left half shadowed.
- Waxing Gibbous: mostly bright moon, shadow crescent on the left side.
- Full Moon: fully bright moon with visible surface detail.
- Waning Gibbous: mostly bright moon, shadow crescent on the right side.
- Last Quarter: left half of the moon bright, right half shadowed.
- Waning Crescent: a slim bright crescent lit on the left side.
