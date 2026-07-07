# Provider 21 - Astronomy

Astronomy is an optional HA-owned content framework for Ditherloom Suite. It is
disabled by default. Each enabled Astronomy card consumes one explicit Home
Assistant slot configured from the Ditherloom app/frame setup.

## Providers

- `astronomy_visible_planets` - Visible Planets.
- `astronomy_moon_watch` - Moon Watch.
- `astronomy_constellation` - Constellation Tonight.
- `astronomy_tonight_sky` - Tonight's Sky.
- `astronomy_overhead` - Planets Overhead.
- `astronomy_conditions` - Astronomy View Conditions.
- `astronomy_solar_activity` - Solar Activity.
- `astronomy_aurora_watch` - Aurora Watch.

All providers reuse the existing cached-content and `frame-awake` Gateway
delivery path. There is no provider-specific delivery route.

## Rendering Contract

- Canvas: 400x300 pixels.
- Backgrounds: bundled Ditherloom astronomy artwork.
- Background processing: RGB artwork is preserved for the shared hybrid
  renderer; no provider-side panel snapping is used.
- Background protection: supplied background pixels are not rewritten to avoid
  panel colours. Foreground text, stars, graph marks, and line work are marked
  with a protected foreground mask so only intentional foreground pixels bypass
  dithering.
- Text: centre-justified, panel-safe white body text with panel-safe yellow
  headings.
- Constellations: panel-safe white line work and panel-safe yellow luxe star
  glyphs, rotated by a local date/hemisphere/longitude orientation term.
- Layout: text is confined to the clear middle areas of the supplied artwork.

Exact white/yellow text and constellation pixels are pasted after the
background pass so the shared hybrid renderer keeps them crisp.

## Astronomy Source And Attribution

Astronomy cards do not fetch third-party horoscope/sky text and V1 does not
bundle external planet photographs. The visible wording is generated from
Ditherloom-owned rules and the current local date/location.

When available, local sky context comes from:

- Skyfield, MIT licensed Python astronomy library.
- jplephem, MIT licensed JPL ephemeris reader.
- JPL/NASA DE421 ephemeris data loaded through Skyfield.
- Open-Meteo cloud cover and visibility data for Astronomy View Conditions.
- NOAA/SWPC Kp, solar-wind, and aurora forecast products for Solar Activity
  and Aurora Watch.

Ditherloom must not claim copyright over Skyfield, jplephem, or NASA/JPL
ephemeris data. The HA attribution sensor and rendered metadata keep these
notices separate from Ditherloom-owned text/art/layout.

NOAA/SWPC data remains NOAA work and is generally public domain unless
otherwise noted; Ditherloom must not imply NOAA endorsement. Open-Meteo remains
CC BY 4.0/terms-controlled. The relevant rendered cards visibly show
`OPEN-METEO` or `NOAA/SWPC` in the footer and retain source metadata.

## Freshness

Astronomy cards are date-bound to the Home Assistant server's local date and
the selected provider id. A cached Astronomy card is stale when its
`astronomy_date` is not today's local date or when its `astronomy_card_provider`
does not match the requested card.

## Release Notes

Keep `THIRD_PARTY_NOTICES.md` and the HA data attribution sensor in sync when
Astronomy source handling changes. If future versions use external planet
images, add source-specific attribution and licensing before bundling or
rendering those images.
