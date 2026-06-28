# Provider 01: Sunrise / Sunset

## Status

Implemented as the first non-weather provider.

## Firmware Commands

No new firmware commands are required.

The provider renders the same kind of 400x300 packed `.ppbin` payload as the
existing weather provider. Delivery reuses the existing Wi-Fi Gateway command
path:

- `PING`
- `BEGIN`
- `B64WRITE`
- `END`
- `DISPLAY`
- `IDLE`

The frame does not need to know this is a Sunrise / Sunset card. It only receives
the already-rendered packed payload and displays the target slot.

## Renderer Rules

- Interface panels, labels, borders, and text use colours from the 30 safe colour
  recipe sheet.
- The current generated sun graphic also uses safe colours.
- Future HQ central artwork may use richer source pixels and be dithered by the
  existing Atkinson-style conversion path.
- Do not globally snap near-safe artwork pixels to the nearest safe colour.
- Preserve dark colours mainly for text, borders, and small contrast details
  because the e-ink panel does not light up.

## Sun Artwork Needed

To make the Sun provider artwork follow the screen state, create these files in
this exact order:

1. `sun_astronomical_twilight_background.png`
2. `sun_civil_dawn_background.png`
3. `sun_sunrise_background.png`
4. `sun_golden_morning_background.png`
5. `sun_daylight_background.png`
6. `sun_golden_evening_background.png`
7. `sun_sunset_background.png`
8. `sun_civil_dusk_background.png`
9. `sun_night_background.png`

Each file should be `400x300`, flat PNG, no transparency.

## ChatGPT Image Prompt

```text
Create 9 separate 400x300 PNG background images for a Ditherloom e-ink Sunrise / Sunset Home Assistant card.

Important: generate the images in this exact order and label each output clearly with its scene name:

1. Astronomical Twilight
2. Civil Dawn
3. Sunrise
4. Golden Morning
5. Daylight
6. Golden Evening
7. Sunset
8. Civil Dusk
9. Night

Each image must use the same scene style and composition: calm water or low horizon, soft clouds, premium quiet atmosphere, broad simple shapes, and enough open space for Home Assistant overlay data.

No text, no numbers, no icons, no UI panels, no border, no logo, no frame mockup.

The device is a small four-colour e-ink panel and does not light up. Keep the images mostly light and readable. Use dark tones only for horizon definition, night sky depth, cloud definition, and small silhouette detail. Avoid large dark blocks, especially for night.

The final app will apply a render-time saturation boost of 20% and contrast boost of 15%, then dither the image. Do not snap artwork to nearest colours.

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

Scene visual rules:
1. Astronomical Twilight: very early pre-dawn or late post-dusk sky, pale warm horizon glow, mostly quiet sky, no large black area.
2. Civil Dawn: soft brightening sky before sunrise, low warm glow at horizon, gentle clouds.
3. Sunrise: sun just crossing the horizon, clear warm glow, visible reflection on water.
4. Golden Morning: sun above horizon, warm soft morning light, bright readable sky.
5. Daylight: light daytime sky, soft clouds, calm water or horizon, not harsh or high contrast.
6. Golden Evening: warm low-angle evening light, rich gold tones, no sun touching horizon yet.
7. Sunset: sun touching or partly below horizon, stronger orange/gold glow and reflection.
8. Civil Dusk: sun below horizon, gentle fading sky, warm afterglow, clouds still visible.
9. Night: moonless or very subtle night horizon, still light enough for e-ink, avoid a full black sky.

Preferred colour balance: warm_white, cream, pale_cream, paper, parchment, pale_yellow, bright_yellow, yellow, gold, peach, tan. For dusk/night use linen, warm_grey, charcoal, burgundy, deep_burgundy, and dark_brown sparingly.

Composition rules:
- Keep the lower third calm enough for overlay data panels.
- Keep the same horizon, cloud style, and colour mood across all 9 images.
- Make each time-of-day scene unmistakable.
- Avoid tiny stars, dense texture, photorealistic clutter, and noisy detail.

Output:
- 9 separate flat PNG images.
- Each image exactly 400x300.
- No transparency.
- Clearly identify each output with the scene name and number.
```
