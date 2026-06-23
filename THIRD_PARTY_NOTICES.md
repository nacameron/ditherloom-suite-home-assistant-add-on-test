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
own licenses. Before public release, generate a full dependency/license report
from the release environment and include the complete notice set required by
those packages.

## Home Assistant Base Image

The add-on Dockerfile currently uses:

```text
ghcr.io/home-assistant/base:latest
```

The Home Assistant base image and its packaged system components are third-party
components. They retain their original licenses and notices.

## Fonts

The add-on Dockerfile installs DejaVu fonts through the base image package
manager. DejaVu fonts and any bundled font files remain under their own font
licenses. The Ditherloom project does not claim copyright over those fonts.

## Weather Data Provider

Open-Meteo is used as the initial free/non-commercial weather data path. Weather
data, API terms, and provider branding remain controlled by Open-Meteo and its
data providers. Keep provider selection configurable before wider release.

