# Ditherloom 30 Safe Colour Recipes

This document defines the 30 safe template colours currently used by the Ditherloom Home Assistant renderer.

The device panel ultimately renders using four physical packet colours:

| Packet colour | Packet RGB |
| --- | --- |
| Black | `0, 0, 0` |
| White | `255, 255, 255` |
| Yellow | `255, 255, 0` |
| Red | `255, 0, 0` |

Most template colours below are simulated with an ordered recipe using those four physical colours.

Recipe columns are proportions in this order:

`red, yellow, white, black`

For example, `0.10, 0.16, 0.74, 0.00` means:

- 10% red
- 16% yellow
- 74% white
- 0% black

Colours marked `solid panel colour` are mapped directly to a physical panel colour rather than a mixed recipe.

## Requirements For Central Weather Images

- Final image area must use only the colours in this table.
- Avoid dense fine detail. The frame is 400x300 and the panel is unforgiving.
- Prefer strong photographic forms with clear silhouettes and broad tonal areas.
- The weather image should fade into warm white, cream, pale cream, parchment, or paper.
- Avoid large dark blocks unless the weather type genuinely needs darkness, such as night or storm.
- Night/storm images still need clear highlight structure so they do not become a noisy black rectangle.
- Use red/orange/yellow accents sparingly but boldly for storm, heat, fire, sun, lightning, hail warning, etc.
- Leave space for the Home Assistant renderer to overlay text and data.

## Safe Colour Table

| Name | RGB | Hex | Recipe red/yellow/white/black |
| --- | --- | --- | --- |
| black | `17, 17, 17` | `#111111` | solid panel colour |
| charcoal | `51, 51, 51` | `#333333` | `0.00, 0.00, 0.16, 0.84` |
| white | `255, 255, 255` | `#FFFFFF` | solid panel colour |
| warm_white | `255, 248, 232` | `#FFF8E8` | `0.00, 0.02, 0.98, 0.00` |
| cream | `255, 237, 190` | `#FFEDBE` | `0.00, 0.14, 0.86, 0.00` |
| pale_cream | `244, 230, 200` | `#F4E6C8` | `0.00, 0.09, 0.91, 0.00` |
| paper | `225, 221, 209` | `#E1DDD1` | `0.00, 0.00, 0.96, 0.04` |
| linen | `185, 176, 160` | `#B9B0A0` | `0.00, 0.00, 0.90, 0.10` |
| warm_grey | `85, 80, 73` | `#555049` | `0.00, 0.00, 0.36, 0.64` |
| yellow | `244, 176, 0` | `#F4B000` | `0.00, 0.70, 0.30, 0.00` |
| bright_yellow | `255, 217, 40` | `#FFD928` | `0.00, 0.90, 0.10, 0.00` |
| pale_yellow | `255, 244, 169` | `#FFF4A9` | `0.00, 0.22, 0.78, 0.00` |
| gold | `217, 145, 0` | `#D99100` | `0.14, 0.72, 0.00, 0.14` |
| dark_gold | `165, 111, 0` | `#A56F00` | `0.08, 0.68, 0.00, 0.24` |
| red | `209, 25, 32` | `#D11920` | solid panel colour |
| warm_red | `196, 74, 92` | `#C44A5C` | `0.62, 0.00, 0.18, 0.20` |
| dark_red | `155, 17, 30` | `#9B111E` | `0.66, 0.00, 0.00, 0.34` |
| burgundy | `110, 31, 53` | `#6E1F35` | `0.42, 0.00, 0.00, 0.58` |
| deep_burgundy | `80, 26, 36` | `#501A24` | `0.28, 0.00, 0.00, 0.72` |
| blush | `255, 226, 226` | `#FFE2E2` | `0.12, 0.00, 0.88, 0.00` |
| peach | `255, 208, 176` | `#FFD0B0` | `0.10, 0.16, 0.74, 0.00` |
| rose | `242, 163, 163` | `#F2A3A3` | `0.22, 0.00, 0.78, 0.00` |
| orange | `230, 106, 26` | `#E66A1A` | `0.50, 0.50, 0.00, 0.00` |
| burnt_orange | `200, 74, 27` | `#C84A1B` | `0.24, 0.66, 0.00, 0.10` |
| terracotta | `182, 90, 60` | `#B65A3C` | `0.42, 0.28, 0.00, 0.30` |
| brown | `140, 90, 43` | `#8C5A2B` | `0.20, 0.24, 0.00, 0.56` |
| dark_brown | `74, 46, 29` | `#4A2E1D` | `0.12, 0.12, 0.00, 0.76` |
| tan | `215, 179, 122` | `#D7B37A` | `0.04, 0.30, 0.56, 0.10` |
| parchment | `247, 222, 179` | `#F7DEB3` | `0.00, 0.04, 0.94, 0.02` |
| maroon | `185, 45, 52` | `#B92D34` | `0.60, 0.05, 0.00, 0.35` |

## Recommended Background/Fade Colours

Use these for the cream fade around the central image:

- `warm_white`
- `cream`
- `pale_cream`
- `paper`
- `parchment`
- `pale_yellow`

## Recommended Highlight Colours

Use these for sun, heat, lightning, warm glow, fire, or alert accents:

- `bright_yellow`
- `yellow`
- `gold`
- `orange`
- `burnt_orange`
- `red`

## Recommended Shadow Colours

Use these for clouds, rain, storm, night, smoke, and depth:

- `paper`
- `linen`
- `warm_grey`
- `charcoal`
- `black`
- `brown`
- `dark_brown`
- `burgundy`
- `deep_burgundy`

## Copyright Note

Custom weather images and custom weather templates created for this integration are copyright Neil Cameron, except for any third-party components or services separately listed in the project notices.
