# Dependency License Snapshot

Snapshot date: 2026-07-02

This file records the Python dependency/license set used for the current
Ditherloom Suite Home Assistant Add On release check. Regenerate this from the
release environment before publishing a release that changes `requirements.txt`,
the Home Assistant add-on image, or the packaged runtime.

## Direct Runtime And Test Dependencies

| Package | Version | License | Source |
| --- | --- | --- | --- |
| fastapi | 0.115.6 | MIT | https://github.com/fastapi/fastapi |
| uvicorn | 0.32.1 | BSD-3-Clause | https://github.com/encode/uvicorn |
| pillow | 11.0.0 | HPND / MIT-CMU style Pillow license | https://github.com/python-pillow/Pillow |
| paho-mqtt | 2.1.0 | EPL-2.0 OR BSD-3-Clause | https://eclipse.dev/paho/ |
| python-multipart | 0.0.20 | Apache-2.0 | https://github.com/Kludex/python-multipart |
| pytest | 8.3.4 | MIT | https://docs.pytest.org/ |

## Installed Transitive Dependencies Observed In `.venv`

| Package | Version | License | Source |
| --- | --- | --- | --- |
| annotated-types | 0.7.0 | MIT | https://github.com/annotated-types/annotated-types |
| anyio | 4.14.0 | MIT | https://github.com/agronholm/anyio |
| click | 8.4.1 | BSD-3-Clause | https://github.com/pallets/click |
| colorama | 0.4.6 | BSD-3-Clause | https://github.com/tartley/colorama |
| h11 | 0.16.0 | MIT | https://github.com/python-hyper/h11 |
| httptools | 0.8.0 | MIT | https://github.com/MagicStack/httptools |
| idna | 3.18 | BSD-3-Clause | https://github.com/kjd/idna |
| iniconfig | 2.3.0 | MIT | https://github.com/pytest-dev/iniconfig |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | https://github.com/pypa/packaging |
| pluggy | 1.6.0 | MIT | https://github.com/pytest-dev/pluggy |
| pydantic | 2.13.4 | MIT | https://github.com/pydantic/pydantic |
| pydantic-core | 2.46.4 | MIT | https://github.com/pydantic/pydantic-core |
| python-dotenv | 1.2.2 | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| PyYAML | 6.0.3 | MIT | https://github.com/yaml/pyyaml |
| starlette | 0.41.3 | BSD-3-Clause | https://github.com/encode/starlette |
| typing-extensions | 4.15.0 | PSF-2.0 | https://github.com/python/typing_extensions |
| typing-inspection | 0.4.2 | MIT | https://github.com/pydantic/typing-inspection |
| watchfiles | 1.2.0 | MIT | https://github.com/samuelcolvin/watchfiles |
| websockets | 16.0 | BSD-3-Clause | https://github.com/python-websockets/websockets |

## Non-Python Runtime Components

| Component | License | Source |
| --- | --- | --- |
| Home Assistant base image | Home Assistant and bundled system component notices apply | https://github.com/home-assistant/docker-base |
| DejaVu fonts | Bitstream Vera / Arev / public-domain DejaVu changes | https://dejavu-fonts.github.io/License.html |
| Barlow / Barlow Condensed | SIL Open Font License 1.1 | https://github.com/jpt/barlow |
