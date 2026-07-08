# Third-Party Notices

This project depends on third-party software and base images. Those components
are not owned by Neil Cameron and are not relicensed under Polycom 1.

## Python Runtime Dependencies

The current prototype uses these Python packages:

| Component | Version | License | Project |
| --- | --- | --- | --- |
| FastAPI | 0.115.6 | MIT | https://github.com/fastapi/fastapi |
| Uvicorn | 0.32.1 | BSD-3-Clause | https://github.com/encode/uvicorn |
| Pillow | 11.0.0 | HPND / MIT-CMU style Pillow license | https://github.com/python-pillow/Pillow |
| Eclipse Paho MQTT | 2.1.0 | EPL-2.0 OR BSD-3-Clause | https://eclipse.dev/paho/ |
| python-multipart | 0.0.20 | Apache-2.0 | https://github.com/Kludex/python-multipart |
| Segno | 1.6.6 | BSD-3-Clause | https://github.com/heuer/segno/ |
| Skyfield | 1.54 | MIT | https://rhodesmill.org/skyfield/ |
| jplephem | 2.24 | MIT | https://github.com/brandon-rhodes/python-jplephem |
| pytest | 8.3.4 | MIT | https://docs.pytest.org/ |

Transitive dependencies are installed by Python packaging tools and retain their
own licenses. The current release dependency notice snapshot is recorded in:

```text
docs/DEPENDENCY_LICENSE_SNAPSHOT.md
```

Regenerate that snapshot from the release environment before each public release
that changes Python dependencies or the base image.

## Home Assistant Base Image

The add-on Dockerfile currently uses:

```text
ghcr.io/home-assistant/base:latest
```

The Home Assistant base image and its packaged system components are third-party
components. They retain their original licenses and notices.

## Fonts

The Home Assistant integration bundles Barlow Condensed and Kalam font files for
stable 400 x 300 e-ink card rendering across Home Assistant hosts.

| Component | License | Project |
| --- | --- | --- |
| Barlow / Barlow Condensed | SIL Open Font License 1.1 | https://github.com/jpt/barlow |
| Kalam | SIL Open Font License 1.1 | https://github.com/google/fonts/tree/main/ofl/kalam |

The bundled Barlow license text is packaged at:

```text
custom_components/ditherloom_suite_ha_addon/assets/fonts/OFL-Barlow.txt
custom_components/ditherloom_suite_ha_addon/assets/fonts/OFL-Kalam.txt
```

Barlow copyright notice:

```text
Copyright 2017 The Barlow Project Authors (https://github.com/jpt/barlow)
```

Kalam copyright notice:

```text
Copyright (c) 2014, Indian Type Foundry (info@indiantypefoundry.com).
```

The add-on Dockerfile may also install DejaVu fonts through the base image
package manager. DejaVu fonts and any bundled font files remain under their own
font licenses. The Ditherloom project does not claim copyright over those fonts.

DejaVu font notice:

```text
Fonts are (c) Bitstream (see below). DejaVu changes are in public domain.
Glyphs imported from Arev fonts are (c) Tavmjong Bah (see below).

Bitstream Vera Fonts Copyright:
Copyright (c) 2003 by Bitstream, Inc. All Rights Reserved. Bitstream Vera is
a trademark of Bitstream, Inc.

Arev Fonts Copyright:
Copyright (c) 2006 by Tavmjong Bah. All Rights Reserved.
```

Full DejaVu license text is published by the DejaVu project:

```text
https://dejavu-fonts.github.io/License.html
```

## Weather Data Provider

Open-Meteo is used as the initial free/non-commercial weather data path. Weather
data, API terms, and provider branding remain controlled by Open-Meteo and its
data providers. Keep provider selection configurable before wider release.

Nominatim/OpenStreetMap is used only as an optional reverse lookup for a display
place name when the user picks a map coordinate without entering a location
name. Results are cached in-process to avoid repeated lookups for the same
coordinate. Nominatim/OpenStreetMap data, API terms, and provider branding
remain controlled by their respective projects.

The optional Weather Radar card can fetch OpenWeather Weather Maps tiles when
the user explicitly enables the radar card and supplies their own OpenWeather
API key in Home Assistant options. Ditherloom does not bundle, share, or claim
ownership of any OpenWeather API key, map tile, provider branding, or terms.
Rendered radar metadata records OpenWeather attribution, terms URL, selected map
layer, and zoom level. The Weather Radar card also fetches and locally caches
OpenStreetMap standard map tiles as the visible basemap underneath the
OpenWeather weather overlay. The selected Ditherloom radar palette is applied
only to semi-transparent OpenWeather overlay pixels, not to the OpenStreetMap
basemap. The composed map is transformed for readability on the Ditherloom 400 x
300 colour display before the normal hybrid renderer packs the card.

Sources:

```text
https://open-meteo.com/
https://openweathermap.org/
https://openweathermap.org/api/weathermaps
https://openweathermap.org/terms
https://www.openstreetmap.org/copyright
https://operations.osmfoundation.org/policies/tiles/
```

## Optional xkcd Comic Content

The optional xkcd Comic provider fetches comic metadata and image assets from
xkcd. xkcd comics are created by Randall Munroe and are not owned by the
Ditherloom project.

Visible rendered xkcd cards include xkcd / Randall Munroe attribution and CC
BY-NC 2.5 license text. Rendered metadata also stores the source comic URL,
image URL, attribution URL, license name, and license URL.

Sources:

```text
https://xkcd.com/
https://xkcd.com/json.html
https://xkcd.com/license.html
https://creativecommons.org/licenses/by-nc/2.5/
```

## Optional Comics Framework Content

The optional Comics framework can fetch comic feeds and image assets from
source-specific publishers when a user explicitly enables that provider and has
configured enough Home Assistant slots on the Ditherloom device. These comics
are not owned by the Ditherloom project. Each rendered comic card includes
source-specific red attribution and license text, and rendered metadata stores
the source URL, image URL, attribution URL, license name, and license URL. For
non-xkcd Comics framework providers, the rendered right-hand attribution strip
also includes a per-comic QR code generated from that rendered comic's exact
source page URL.

All comic sources pass through the shared Ditherloom Comics suitability selector
and 400 x 300 hybrid renderer before they can be cached for delivery. Bundled
settings-page samples are static 400 x 300 Atkinson-filtered colour previews
with undithered panel-safe red attribution and source QR code. Unsuitable
content fails closed instead of being rendered unreadably on the device.

### Diesel Sweeties

Diesel Sweeties comics are by R. Stevens and are licensed CC BY-NC 2.5.

Sources:

```text
https://www.dieselsweeties.com/
https://creativecommons.org/licenses/by-nc/2.5/
```

### Mimi & Eunice

Mimi & Eunice cartoons are by Nina Paley and are licensed CC BY-SA.

Sources:

```text
https://mimiandeunice.com/
https://mimiandeunice.com/about/
https://creativecommons.org/licenses/by-sa/3.0/
```

## Optional Daily Astrology Content

Daily Astrology uses Ditherloom-owned/generated horoscope wording and bundled
sign artwork supplied for the Ditherloom project. It does not fetch or embed
third-party horoscope copy.

When available, the provider uses Skyfield and jplephem to calculate planetary
and lunar positions from JPL/NASA ephemeris data. Skyfield and jplephem remain
under their MIT licenses. JPL/NASA ephemeris data remains NASA/JPL work under
its source distribution terms; the Ditherloom project does not claim copyright
over that data or over Skyfield/jplephem.

Sources:

```text
https://rhodesmill.org/skyfield/
https://github.com/brandon-rhodes/python-jplephem
https://naif.jpl.nasa.gov/naif/data.html
```

## Optional Astronomy Content

Astronomy cards use Ditherloom-owned/generated sky summary wording and bundled
astronomy artwork supplied for the Ditherloom project. V1 does not bundle
external planet photographs or scrape third-party sky text.

When available, the provider uses Skyfield and jplephem to calculate local sky
positions from JPL/NASA DE421 ephemeris data. Skyfield and jplephem remain under
their MIT licenses. JPL/NASA ephemeris data remains NASA/JPL work under its
source distribution terms; the Ditherloom project does not claim copyright over
that data or over Skyfield/jplephem.

Rendered Astronomy metadata records Ditherloom attribution, Skyfield/jplephem
secondary attribution, JPL/NASA ephemeris attribution, the selected card type,
date, configured location, and whether Skyfield data or fallback seasonal
guidance was used.

Astronomy View Conditions uses Open-Meteo cloud cover and visibility data for the
configured locale. Open-Meteo remains under its own CC BY 4.0/terms, and the
rendered card visibly attributes Open-Meteo when that card is used.

Solar Activity and Aurora Watch use NOAA/SWPC space-weather data, including Kp,
solar-wind, and aurora forecast products where available. NOAA/NWS information
is generally public domain unless otherwise noted, but NOAA/SWPC remains the
source and Ditherloom does not imply NOAA endorsement or claim copyright over
NOAA data. Rendered cards visibly attribute NOAA/SWPC when those cards are used.

Sources:

```text
https://rhodesmill.org/skyfield/
https://github.com/brandon-rhodes/python-jplephem
https://naif.jpl.nasa.gov/naif/data.html
https://open-meteo.com/
https://www.swpc.noaa.gov/
https://services.swpc.noaa.gov/
https://www.weather.gov/disclaimer
```
