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

The Home Assistant integration bundles Barlow Condensed font files for stable
400 x 300 e-ink card rendering across Home Assistant hosts.

| Component | License | Project |
| --- | --- | --- |
| Barlow / Barlow Condensed | SIL Open Font License 1.1 | https://github.com/jpt/barlow |

The bundled Barlow license text is packaged at:

```text
custom_components/ditherloom_suite_ha_addon/assets/fonts/OFL-Barlow.txt
```

Barlow copyright notice:

```text
Copyright 2017 The Barlow Project Authors (https://github.com/jpt/barlow)
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
