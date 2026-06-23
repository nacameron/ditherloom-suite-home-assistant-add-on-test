# Ditherloom Suite Home Assistant Add On

Public test repository for the Ditherloom Suite Home Assistant integration.

## Preferred install path

Full public install instructions are in [docs/INSTALL.md](docs/INSTALL.md).

Short version:

1. Open HACS.
2. Open custom repositories.
3. Add:

   ```text
   https://github.com/nacameron/ditherloom-suite-home-assistant-add-on-test
   ```

4. Choose category `Integration`.
5. Install `Ditherloom Suite Home Assistant Add On`.
6. Restart Home Assistant.
7. Go to Settings > Devices & services > Add integration.
8. Search for `Ditherloom` or `Ditherloom Suite Home Assistant Add On`.

## MQTT Is Optional

MQTT is not required for the current prototype setup. The integration can send
to the frame directly over the frame's Wi-Fi Gateway host/IP and port while the
frame is awake.

If the Home Assistant MQTT integration is configured, Ditherloom will also
publish optional job metadata to the configured topic base. If MQTT is not
configured, that publish step is skipped.

## Update Alerts

The integration creates a diagnostic Home Assistant update entity. Home
Assistant checks the latest GitHub release every 30 minutes and can show when
the installed custom integration is behind.

HACS remains the install and redownload route. This update entity does not
install files by itself.

## Weather Display Options

Weather cards can render in `colour` or `mono` mode. `colour` is the default and
uses the Ditherloom palette-safe colour recipes. `mono` keeps the same larger,
high-contrast layout but restricts the card to black and white.

Weather payloads use the physical-frame orientation correction confirmed from
device photo testing.

Location privacy notes are in [PRIVACY.md](PRIVACY.md).

## Wi-Fi Wake Sync

The integration adds a `Synchronise Wi-Fi wake window` button entity. Use it
while the frame is awake on Wi-Fi to import the firmware-owned Home Assistant
timer settings from `HACONFIG` and `SLEEPINFO`.
The imported interval and wake-window seconds are then used for Home Assistant
job expiry timing. The button reads the frame timer; it does not write a new
timer to the frame.

## If It Does Not Appear In Add Integration

There is no expected long delay after restart. If it does not appear:

1. Confirm HACS installed it as category `Integration`, not as an app/add-on.
2. In HACS, open the integration and confirm it says installed.
3. Confirm this folder exists on the Home Assistant server:

   ```text
   /config/custom_components/ditherloom_suite_ha_addon
   ```

4. Confirm this file exists:

   ```text
   /config/custom_components/ditherloom_suite_ha_addon/manifest.json
   ```

5. Restart Home Assistant again after the files are present.
6. Search Add integration for `Ditherloom`.
7. If it still does not appear, check Settings > System > Logs for:

   ```text
   ditherloom_suite_ha_addon
   ```

If HACS was added before this repository had the custom integration files, remove
the custom repository from HACS, add it again as category `Integration`, install
again, and restart Home Assistant.

If HACS says:

```text
Repository 'nacameron/ditherloom-suite-home-assistant-add-on-test' exists in the store.
```

then the repository is already registered. Close the custom repository dialog,
search HACS for `Ditherloom`, open the existing store entry, and install or
redownload the integration from there.

## What it currently does

- Renders a Ditherloom weather card inside Home Assistant.
- Uses Open-Meteo for free/non-commercial test weather.
- Resolves a map-picked weather location name when one is not entered manually.
- Uses a Home Assistant map picker for weather action location, with manual
  latitude/longitude fields kept as fallback.
- Serves a `.ppbin` payload through a Home Assistant HTTP endpoint.
- Serves a preview PNG endpoint.
- Publishes optional MQTT job metadata if MQTT is configured.
- Can attempt the existing Wi-Fi Gateway command path while the frame is awake:
  `PING`, `BEGIN`, `B64WRITE`, `END`, `DISPLAY`, `IDLE`.
- Adds a Home Assistant update entity that checks the latest GitHub release.
- Supports colour or mono weather display mode.
- Adds a Wi-Fi wake-window sync button that does not alter frame timer settings.
- Adds dashboard-friendly entities for preview, render, send, sync, and status.

## Dashboard

A starter dashboard card is documented in [docs/DASHBOARD.md](docs/DASHBOARD.md).

## License

Project license: Polycom 1. Ditherloom-specific source, custom renderer rules,
custom device-screen graphics, and project documentation are copyright Neil
Cameron. Third-party components keep their original licenses and notices; see
`THIRD_PARTY_NOTICES.md`.
