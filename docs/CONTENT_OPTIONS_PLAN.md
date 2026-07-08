# Provider-by-provider Content Options Plan

This plan covers future Ditherloom Suite Home Assistant content providers.
Open-Meteo Weather is intentionally excluded because the current build already
has that provider. Provider 00 now includes separately selectable Weather
sub-cards, including Weather Radar with a cached OpenStreetMap basemap,
OpenWeather weather overlay, a user-selected Ditherloom-safe radar palette, and
an on-card colour scale below the radar image.

The rule for every provider is simple: add one complete function at a time,
prove it works, then move to the next provider.

## Existing Baseline

The add-on already has:

- Open-Meteo weather fetching.
- 400x300 Ditherloom-safe rendering.
- `.ppbin` payload generation.
- Preview PNG serving.
- Optional MQTT job metadata.
- Frame-awake delivery through the Wi-Fi Gateway path.
- Dashboard/status/update entities.

Every provider below must reuse the locked render delivery pathway in
`docs/LOCKED_RENDER_DELIVERY_PATHWAY.md`: Home Assistant refreshes and caches
the payload first, the frame announces that it is awake, and Home Assistant sends
the already-rendered packed payload through the existing Gateway command path.

Do not create provider-specific send paths.

## Per-provider Definition Of Done

Each provider is only considered complete when it has:

1. A provider module with fetch, normalize, render, cache, and error handling.
2. A Home Assistant enable/disable option.
3. Any required provider settings, such as location, region, API key, or units.
4. Fixture data for offline render tests.
5. A rendered preview PNG.
6. A packed `.ppbin` payload with correct length and CRC metadata.
7. Attribution/license text stored with the rendered card.
8. A graceful unavailable/error card.
9. Documentation for source, refresh interval, and attribution.
10. Reuse of the existing frame-awake Gateway delivery path.

## Foundation Step: Provider Framework

Before adding the first new provider, add the shared provider framework.

Function added: content provider registry.

Work:

- Add a provider registry.
- Add a shared normalized card schema.
- Add shared content metadata fields: provider id, title, source, attribution,
  rendered time, expiry time, preview URL, CRC, packed length, and Gateway delivery metadata.
- Generalize current weather-only naming where needed so cached payloads can be
  content-type aware.
- Add fixture-based render tests for non-weather cards.
- Keep the existing Open-Meteo Weather behavior unchanged.

Done when:

- Existing weather rendering still works.
- A static fixture provider can render a preview and packed payload without
  talking to a live API.
- The frame-awake delivery path still sends the cached payload.

## Provider 1: Sunrise / Sunset

Function added: daily sun card.

Status: implemented. See `docs/PROVIDER_01_SUNRISE_SUNSET.md`.

Shows:

- Sunrise.
- Sunset.
- Civil twilight.
- Day length.
- Golden hour.

Why first:

- Very lightweight.
- Excellent e-ink fit.
- Location-based but low privacy risk.
- Slow daily refresh.

Implementation:

- Use Home Assistant location by default.
- Allow manual latitude/longitude override.
- Cache until the next local day or a configured daily refresh time.
- Render with `timeline` or `metric_grid`.

Done when:

- The card renders with fixture data.
- The provider renders from configured location.
- Missing location shows a clear setup-required card.

## Provider 2: Moon Phase

Function added: moon card.

Status: implemented with phase-aware artwork selection. See `docs/PROVIDER_02_MOON_PHASE.md`.

Shows:

- Current phase.
- Illumination percentage.
- Moonrise.
- Moonset.
- Optional next full/new moon date.

Why second:

- Pairs naturally with Sunrise / Sunset.
- Attractive low-refresh display.
- Good test of simple astronomy calculations and timeline rendering.

Implementation:

- Reuse location settings from Provider 1.
- Cache daily or twice daily.
- Render with `score_card` or `timeline`.

Done when:

- The card renders from fixture data.
- Illumination and phase text fit the 400x300 layout.
- It can rotate with Sunrise / Sunset without changing delivery behavior.

## Provider 3: Public Holidays

Function added: public holiday countdown card.

Shows:

- Next public holiday.
- Date.
- Countdown.
- Long-weekend hint where possible.

Why third:

- Useful global utility card.
- Low refresh rate.
- Exercises country/region configuration.

Implementation:

- Add country/region selector.
- Cache daily.
- Render with `daily_fact` or `timeline`.
- If source coverage is missing, show region-not-supported.

Done when:

- Country/region config is saved.
- Fixture tests cover at least one normal holiday and one no-upcoming-holiday case.
- Attribution/source metadata appears on the rendered card.

## Provider 4: Earthquake Feed

Function added: nearby earthquake card.

Shows:

- Recent nearby earthquakes.
- Magnitude.
- Distance.
- Time.
- Optional alert threshold.

Why fourth:

- Useful ambient data.
- Good first provider with location filtering and recency logic.

Implementation:

- Use Home Assistant location by default.
- Add radius and minimum magnitude options.
- Cache on a conservative interval.
- Render with `alert_card` when a threshold is met, otherwise `timeline`.

Done when:

- Fixture tests cover no recent quakes and one nearby quake.
- Distance and time formatting are readable.
- The provider never floods the frame with frequent refreshes.

## Provider 5: Quote Card

Function added: public-domain quote card.

Shows:

- Quote.
- Author.
- Source where available.

Why fifth:

- Simple text-only renderer.
- Good test of content length limits.
- Useful as a fallback/rotation card.

Implementation:

- Use a curated public-domain quote source or bundled public-domain fixture list.
- Do not use unclear quote APIs.
- Cache daily.
- Render with `daily_fact`.

Done when:

- Long quotes wrap cleanly or are rejected before rendering.
- Public-domain source metadata is recorded.
- No quote renders without an author/source fallback.

## Provider 6: Open-Meteo Air Quality

Function added: air quality card.

Shows:

- PM2.5.
- PM10.
- Ozone.
- Dust.
- Pollen where available.
- AQI-style display.

Why sixth:

- Builds on the existing Open-Meteo integration style without touching the
  already-built Open-Meteo Weather provider.
- Good slow-refresh e-ink data.

Implementation:

- Keep it as a separate provider from weather.
- Reuse location/unit settings where appropriate.
- Cache on a conservative interval.
- Render with `metric_grid` and optional `score_card`.

Done when:

- Missing/unavailable pollutant fields degrade cleanly.
- Attribution is shown separately from weather attribution if needed.
- Weather provider behavior is unchanged.

## Provider 7: Astronomy Visibility

Function added: stargazing conditions card.

Shows:

- Cloud cover.
- Moonlight impact.
- Visibility score.
- Short recommendation.

Why seventh:

- Combines already-added astronomy concepts with weather-style data.
- Useful but should wait until the simpler astronomy cards are stable.

Implementation:

- Use simple, explainable scoring rules.
- Reuse weather/cloud data if already cached.
- Reuse moon provider data if available.
- Render with `score_card`.

Done when:

- The score is deterministic from fixture data.
- The card explains the main blocker: cloud, moonlight, rain, or daylight.
- It does not require a new delivery path.

## Provider 8: Rain Radar Summary

Function added: rain-nearby summary card.

Shows:

- Textual rain-nearby summary.
- Direction/distance where the source supports it.
- Short now/soon status.

Why eighth:

- Useful weather-adjacent function.
- Needs care to avoid map tile licensing problems.

Implementation:

- Do not use map tiles by default.
- Use only a source that permits derived text summaries.
- Render with `alert_card` or `metric_grid`.

Done when:

- The provider works without rendering licensed map imagery.
- The source and attribution are explicit.
- Unsupported regions show a setup/unavailable card.

## Provider 9: NASA APOD

Function added: astronomy picture card.

Shows:

- APOD title.
- Date.
- Short explanation.
- Image only when licensing permits.

Why ninth:

- High appeal, but needs copyright-aware filtering.

Implementation:

- Add API key support if required.
- Filter out copyrighted or unsupported media before rendering.
- Use image mode only when the image is permitted and suitable for e-ink.
- Fall back to text-only APOD card.

Done when:

- Copyrighted items do not render as image cards.
- Text-only fallback works.
- Attribution and source URL are stored.

## Provider 10: xkcd Comic

Function added: xkcd comic card.

Shows:

- Latest or random comic.
- Title.
- Alt text.
- Comic image where suitable.

Why tenth:

- Strong e-ink fit.
- Needs text/image layout handling and license attribution.

Implementation:

- Add opt-in latest/random mode with optional explicit comic number for testing.
- Convert image through the Ditherloom hybrid renderer after suitability checks.
- Reject comics that are too tall, too small, too dense, too full of tiny
  detail, or dependent on blue/green/cyan/purple/magenta hues the display
  cannot reproduce well.
- Permit warm/red/yellow/orange/brown colour when it remains legible on the
  400x300 display.
- Render title and visible xkcd / Randall Munroe CC BY-NC 2.5 attribution
  without overflowing.
- Store alt text, source URL, image URL, attribution URL, license name, license
  URL, and suitability metrics in metadata.
- Cache per selected/random comic on the normal Home Assistant provider refresh
  interval.

Done when:

- Image conversion is readable on 400x300.
- Busy comics fail closed instead of being rendered.
- Alt text is stored in metadata.
- Attribution/license text is visible on-card and present in metadata.

## Provider 11: Wikimedia Today

Function added: Wikimedia daily knowledge card.

Shows:

- On this day.
- Featured article.
- Random fact.
- Featured image where license metadata is clear.

Why eleventh:

- Powerful content source but attribution-heavy.

Implementation:

- Prefer text-first cards initially.
- Store title, source URL, author/license where supplied.
- Only render images when license metadata is available.

Done when:

- Attribution metadata survives fetch, normalize, render, and cache.
- Image cards can be disabled.
- Unsupported/missing license data falls back to text.

## Provider 12: Today In History

Function added: history digest card.

Shows:

- Short events for today’s date.
- Year.
- Event summary.

Why twelfth:

- Similar to Wikimedia but simpler if using a clean licensed source.

Implementation:

- Use only open/licensed data.
- Limit to 2-4 events.
- Cache daily.
- Render with `daily_fact` or `timeline`.

Done when:

- Events fit without tiny text.
- Source/license is recorded.
- The provider rejects unknown-license data.

## Provider 13: Word Of The Day

Function added: word card.

Shows:

- Word.
- Definition.
- Example sentence.

Why thirteenth:

- Good text card, but source licensing needs checking first.

Implementation:

- Choose a source only after license review.
- Cache daily.
- Render with `daily_fact`.

Done when:

- Definition and example text fit.
- Source license is documented.
- Missing daily word shows graceful unavailable state.

## Provider 14: OpenAQ Air Quality

Function added: real-world sensor air quality card.

Shows:

- Nearby sensor location.
- PM2.5/PM10 or available pollutants.
- Last measurement time.

Why fourteenth:

- More local than model-based air quality.
- May require API key and source-specific setup.

Implementation:

- Add API key option if required.
- Add search radius.
- Show stale-data age clearly.
- Render with `metric_grid`.

Done when:

- No-nearby-sensor state is clear.
- Stale sensor data is marked.
- API-key missing state is clear.

## Provider 15: GTFS Transit

Function added: stop board card.

Shows:

- Next departures.
- Route names.
- Times/countdowns.
- Service alerts where available.

Why fifteenth:

- High utility but region/feed setup varies heavily.

Implementation:

- Add feed URL/source configuration.
- Add stop id selector or manual stop id.
- Keep feed license notes per configured agency.
- Render with `timeline`.

Done when:

- A fixture feed renders next departures.
- Feed/license metadata is stored.
- Missing stop/feed config shows setup-required.

## Provider 16: Open Charge Map EV

Function added: EV charger card.

Shows:

- Nearby chargers.
- Connector type.
- Distance.
- Availability where supported.

Why sixteenth:

- Useful garage/EV display.
- Availability varies, so fallback behavior matters.

Implementation:

- Add connector filter.
- Add radius.
- Cache conservatively.
- Render with `timeline` or `metric_grid`.

Done when:

- Availability missing does not look like availability false.
- Connector labels fit.
- Attribution/source metadata is present.

## Provider 17: Tide / Marine Conditions

Function added: tide and marine card.

Shows:

- Next high/low tides.
- Swell.
- Wind.
- Marine forecast summary.

Why seventeenth:

- Useful for coastal users.
- Source depends strongly on region.

Implementation:

- Add region/source selection.
- Add nearest station selection where needed.
- Render with `timeline`.

Done when:

- Unsupported inland/region state is clear.
- Tide times fit cleanly.
- Source-specific attribution is recorded.

## Provider 18: Fire Danger / Alerts

Function added: local warning card.

Shows:

- Warning level.
- Fire danger rating.
- Emergency notices where available.

Why eighteenth:

- Useful but safety-sensitive and region-specific.

Implementation:

- Treat as informational, not life-safety authoritative.
- Add country/region-specific providers.
- Cache carefully but do not over-poll.
- Render with `alert_card`.

Done when:

- Disclaimer/source timestamp is visible.
- Region-specific source is documented.
- Alerts degrade safely when unavailable.

## Provider 19: Open Food Facts

Function added: product lookup card.

Shows:

- Product name.
- Barcode lookup result.
- Allergens.
- Nutri-Score.
- Pantry/product notes.

Why nineteenth:

- Kitchen-friendly, but less ambient than the earlier cards.

Implementation:

- Add manual barcode input or Home Assistant service call.
- Respect attribution/share-alike requirements.
- Render with `daily_fact` or `metric_grid`.

Done when:

- Missing product lookup is clear.
- Allergens are prominent.
- Attribution/share-alike handling is documented.

## Provider 20: ISS / Satellite Passes

Function added: visible pass card.

Shows:

- Next visible ISS pass.
- Start time.
- Duration.
- Max elevation.

Why twentieth:

- Cool ambient display.
- Location required but otherwise contained.

Implementation:

- Use location config.
- Cache until next pass changes.
- Render with `timeline` or `score_card`.

Done when:

- No-visible-pass state is clear.
- Times are local.
- Fixture tests cover one pass and no pass.

## Provider 21: NOAA / SWPC Space Weather

Function added: space weather card.

Shows:

- Aurora chance/geomagnetic status.
- Solar flare status.
- Geomagnetic storm level.

Why twenty-first:

- Strong ambient data card.
- Best after the provider framework and alert template are mature.

Implementation:

- Cache conservatively.
- Render with `score_card` or `alert_card`.
- Keep source timestamp visible.

Done when:

- Quiet, watch, and storm states render distinctly.
- Source timestamp and attribution are present.
- The provider has an unavailable card.

## Rotation After Providers Exist

## Implemented Astronomy Framework

Function added: astronomy card framework.

Status: implemented local-staged V1. See `docs/PROVIDER_21_ASTRONOMY.md`.

Provider ids:

- `astronomy_visible_planets`
- `astronomy_moon_watch`
- `astronomy_constellation`
- `astronomy_tonight_sky`
- `astronomy_overhead`
- `astronomy_conditions`
- `astronomy_solar_activity`
- `astronomy_aurora_watch`

The Astronomy framework is disabled by default. Each enabled card consumes one
explicit HA slot and reuses the existing cached-content and frame-awake Gateway
delivery path. It uses bundled Ditherloom astronomy artwork, panel-safe
white/yellow text and constellation marks, protected foreground masks, and no
provider-side panel snapping or exact-colour mutation of supplied backgrounds.

Attribution:

- Ditherloom owns the generated wording, layout, code, and bundled project
  artwork.
- Skyfield and jplephem remain MIT licensed.
- JPL/NASA DE421 ephemeris data remains NASA/JPL work; Ditherloom does not
  claim copyright over that data.
- Open-Meteo is used for Astronomy View Conditions cloud/visibility data and remains
  CC BY 4.0/terms-controlled.
- NOAA/SWPC is used for Solar Activity and Aurora Watch Kp, solar-wind, and
  aurora products. NOAA/SWPC remains the source; Ditherloom does not claim
  copyright over NOAA data or imply NOAA endorsement.

Only add rotation after at least three non-weather providers are complete.

Function added: content rotation.

Work:

- Let users choose enabled providers.
- Let users choose order or automatic rotation.
- Keep one cached payload ready before the frame wakes.
- Do not let rotation create multiple jobs per wake unless explicitly configured.

Done when:

- Rotation can switch between completed providers without changing the Gateway
  delivery path.
- Disabled providers never render or publish.
- The dashboard shows which provider is currently cached.
