# Ditherloom Suite Home Assistant Add On

Prototype Home Assistant add-on for rendering Ditherloom content cards,
serving packed payloads, and publishing MQTT jobs to a modified Ditherloom frame.

This add-on is the runtime side. The Ditherloom Suite desktop app should only
configure the Home Assistant integration on the frame.

## Preferred install path

This repository also contains a Home Assistant custom integration at:

```text
custom_components/ditherloom_suite_ha_addon
```

Use HACS custom repositories and choose category `Integration`, then add this
repo:

```text
https://github.com/nacameron/ditherloom-suite-home-assistant-add-on-test
```

After installing and restarting Home Assistant, add it from:

```text
Settings > Devices & services > Add integration
```

## Current prototype

- Weather card renderer.
- Open-Meteo free/non-commercial test provider.
- Strong four-colour Ditherloom display preview.
- Packed `.ppbin` output.
- CRC32 metadata.
- MQTT `cmd/job` publishing.
- Local payload serving.

## License

Project license: Polycom 1. Ditherloom-specific source, custom renderer rules,
custom device-screen graphics, and project documentation are copyright Neil
Cameron. Third-party components keep their original licenses and notices; see
the repository `THIRD_PARTY_NOTICES.md`.

## Payload URL

The frame needs a direct local URL, not the Home Assistant Ingress URL. Configure
the add-on with a base URL reachable from the frame, for example:

```text
http://homeassistant.local:8099
```

The current weather payload is served at:

```text
/payloads/weather-current.ppbin
```

## Runtime model

Production behavior should be sleep-first and repeating: the frame wakes on a
configured Home Assistant update schedule, opens its Wi-Fi Gateway window,
receives the latest intended update job, validates/displays it, acknowledges it,
returns to `IDLE`/`SLEEP`, then wakes again on the next configured update.
