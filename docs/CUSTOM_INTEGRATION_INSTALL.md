# Installing As A Home Assistant Custom Integration

Use this route when Home Assistant Apps/Add-ons are unavailable or unstable.

## HACS Custom Repository

1. Open HACS.
2. Open the menu.
3. Choose custom repositories.
4. Add this repository URL:

   ```text
   https://github.com/nacameron/ditherloom-suite-home-assistant-add-on-test
   ```

5. Select category `Integration`.
6. Install `Ditherloom Suite Home Assistant Add On`.
7. Restart Home Assistant.
8. Go to Settings > Devices & services > Add integration.
9. Search for `Ditherloom Suite Home Assistant Add On`.

## MQTT Is Optional

MQTT is not required for the current prototype setup. The integration can send
to the frame directly over the frame's Wi-Fi Gateway host/IP and port while the
frame is awake.

If the Home Assistant MQTT integration is configured, Ditherloom will also
publish optional job metadata to the configured topic base. If MQTT is not
configured, that publish step is skipped.

## Manual Custom Component Install

If HACS is not available, copy this folder into Home Assistant:

```text
custom_components/ditherloom_suite_ha_addon
```

Then restart Home Assistant and add the integration from:

```text
Settings > Devices & services > Add integration
```

## Current Integration Behavior

The custom integration:

- renders the Ditherloom weather card inside Home Assistant,
- fetches Open-Meteo data for free/non-commercial testing,
- serves the latest `.ppbin` payload through a Home Assistant HTTP endpoint,
- serves a preview PNG endpoint,
- publishes optional MQTT job metadata if the MQTT integration is configured,
- can try the existing Wi-Fi Gateway command path directly:
  - `PING`
  - `BEGIN`
  - `B64WRITE`
  - `END`
  - `DISPLAY`
  - `IDLE`

The direct Wi-Fi Gateway path only works while the frame is awake and listening.
The production model remains a repeating scheduled wake/update/sleep cycle.

## Services

After setup, the integration registers:

```text
ditherloom_suite_ha_addon.render_weather_card
ditherloom_suite_ha_addon.send_weather_card
```

`render_weather_card` renders and stores the payload/preview.

`send_weather_card` renders, publishes optional MQTT metadata when available,
attempts to send via the existing Wi-Fi Gateway path, displays the reserved
content slot, then requests `IDLE`.

## Reserved Slot

The default reserved Home Assistant content slot is `445`.

Change it in the integration options if the frame/app later reserves a different
slot. Do not point this integration at normal gallery/memo slots without an
explicit test plan.
