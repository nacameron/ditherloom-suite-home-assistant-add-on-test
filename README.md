# Ditherloom Suite Home Assistant Add On

Public test repository for the Ditherloom Suite Home Assistant integration.

## Preferred install path

Use HACS custom repositories:

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
8. Search for `Ditherloom Suite Home Assistant Add On`.

## What it currently does

- Renders a Ditherloom weather card inside Home Assistant.
- Uses Open-Meteo for free/non-commercial test weather.
- Serves a `.ppbin` payload through a Home Assistant HTTP endpoint.
- Serves a preview PNG endpoint.
- Publishes MQTT job metadata if MQTT is configured.
- Can attempt the existing Wi-Fi Gateway command path while the frame is awake:
  `PING`, `BEGIN`, `B64WRITE`, `END`, `DISPLAY`, `IDLE`.

## License

Project license: Polycom 1. Ditherloom-specific source, custom renderer rules,
custom device-screen graphics, and project documentation are copyright Neil
Cameron. Third-party components keep their original licenses and notices; see
`THIRD_PARTY_NOTICES.md`.

