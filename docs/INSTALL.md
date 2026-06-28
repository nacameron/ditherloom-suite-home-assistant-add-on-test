# Ditherloom Suite Home Assistant Add On Install Guide

This guide installs the Ditherloom Suite Home Assistant Add On as a Home
Assistant custom integration through HACS.

This is not a Home Assistant add-on, app, or helper. It appears in Home
Assistant under integrations after it has been installed and Home Assistant has
been restarted.

## What You Need

- Home Assistant running on your network.
- HACS installed and configured in Home Assistant.
- A modified Ditherloom frame on Wi-Fi-capable firmware.
- The frame-side Home Assistant configuration written by Ditherloom Suite.
- The frame Wi-Fi Gateway host/IP and port. The default Gateway port is `5757`.
- Home Assistant and the frame on the same reachable local network.

MQTT is optional. The integration can send directly to the frame over the
frame's Wi-Fi Gateway while the frame is awake.

## Install Through HACS

1. Open **HACS** in Home Assistant.
2. Open the three-dot menu in the top-right corner.
3. Select **Custom repositories**.
4. Add this repository URL:

   ```text
   https://github.com/nacameron/ditherloom-suite-home-assistant-add-on-test
   ```

5. Set the repository type to **Integration**.
6. Select **Add**.
7. Search HACS for **Ditherloom**.
8. Open **Ditherloom Suite Home Assistant Add On**.
9. Select **Download**.
10. Download the latest version.
11. Restart Home Assistant.

HACS documentation for custom repositories is here:
https://www.hacs.xyz/docs/faq/custom_repositories/

## Add The Integration In Home Assistant

After restarting Home Assistant:

1. Go to **Settings > Devices & services**.
2. Select **Add integration**.
3. Search for **Ditherloom**.
4. Select **Ditherloom Suite Home Assistant Add On**.
5. Fill in the setup fields.

## Setup Fields

Use the values shown in the Ditherloom Suite Home Assistant setup screen.

| Field | Meaning |
| --- | --- |
| `Library ID` | The frame/library identity created by Ditherloom Suite. |
| `Frame Wi-Fi host/IP` | The frame's live Wi-Fi Gateway host or IP address. |
| `Frame Gateway port` | Usually `5757`. |
| `MQTT topic base` | Optional. Defaults to `ditherloom/<library_id>`. |
| `Location name` | Weather display location label. |
| `Latitude` / `Longitude` | Weather lookup coordinates. |
| `Repeating update interval minutes` | How often Home Assistant refreshes the waiting weather card. |
| `Wake window minutes` | Used for job expiry metadata. The firmware still owns the real wake window. |
| `Max jobs per wake` | Currently `1`. |
| `Target slot` | Reserved frame slot. Default `445`. |
| `Display mode` | `colour` or `mono`. |
| `Temperature unit` | `celsius` or `fahrenheit`. Controls current, high, low, and feels-like values. |
| `Wind speed unit` | `kmh` or `mph`. Controls the wind speed shown on weather cards. |

The frame owns the real Home Assistant schedule. Home Assistant only keeps the
weather card freshly rendered and waits for the frame to announce that it is
awake.

## Frame-Awake Delivery

The integration exposes two firmware endpoints for the configured integration
entry:

```text
/api/ditherloom/<entry_id>/frame-awake
/api/ditherloom/<entry_id>/frame-sleeping
```

The Ditherloom Suite app should not ask the user to type the `entry_id`. After
the user enters the Home Assistant URL and access token, the app can ask this
integration for the correct callback paths:

```text
GET /api/ditherloom/discovery
```

If more than one Ditherloom integration entry is configured, the app should call
the same endpoint with the library ID:

```text
GET /api/ditherloom/discovery?library_id=<library_id>
```

This endpoint returns the installed integration entry ID, the frame-awake and
frame-sleeping callback paths, and a `config` object that the app can write into
the frame's `HACONFIG`. The firmware should use those saved callback paths when
it wakes; it should not try to discover the Home Assistant entry ID itself.

When the frame wakes, firmware posts to `frame-awake` with its live Gateway IP,
port, serial/library identity, and target slot. Home Assistant immediately
starts sending the already-rendered packed weather payload through the existing
Wi-Fi Gateway command path.

When the frame is finished and about to sleep, firmware may post to
`frame-sleeping` so the Home Assistant device page records the sleep event.

The Ditherloom device page exposes **Frame handshake status**. It shows whether
weather is ready, whether the frame has announced awake, and whether the latest
delivery succeeded.

## Test Weather Rendering

After setup:

1. Open the Ditherloom integration device in Home Assistant.
2. Press **Render weather preview**.
3. Check the **Weather preview** image entity.
4. Wake the frame with firmware that posts to the `frame-awake` endpoint.
5. Confirm **Frame handshake status** changes to `delivered`.

Weather data is fetched from Open-Meteo. The optional place-name lookup uses
Nominatim/OpenStreetMap when a map-picked location needs a display name. See
`PRIVACY.md` for location privacy notes.

The integration setup and options pages include a map picker for the shared
weather, sunrise/sunset, and moon phase location. Manual latitude/longitude
fields remain available as fallback and are updated from the picked map point.

The integration options landing page is split into buttons for Weather,
Sunrise / Sunset, Moon Phase, Display Rotation, and Device / Connection. Weather
stays enabled by default for existing installs. Sunrise / Sunset and Moon Phase
are opt-in. If two or more content pages are enabled, Home Assistant keeps each
enabled card cached in its own HA-owned slot. If Display Rotation is enabled,
Home Assistant uses the configured hours/minutes interval to choose which HA
slot to display explicitly.

If more than one content page is enabled, configure enough explicit Home
Assistant-owned slots. The reserved slot is used first. Extra slots must be
listed in **Additional Home Assistant slot pool** such as `442,443` or
`442-444`. The integration does not guess or reuse normal gallery, memo, image,
or system slots.

Before writing any HA-rendered payload, Home Assistant marks and verifies the
target slot through Gateway:

```text
SETSLOTCLASS <slot> ha
SLOTCLASS <slot>
```

The expected class check is `class=ha`, `value=3`, and
`rotation_selectable=0`.

## Dashboard

A starter dashboard card is provided in:

```text
docs/DASHBOARD.md
```

Entity IDs can vary by Home Assistant install. Open the Ditherloom device page,
copy the real entity IDs, then replace the example IDs in the dashboard YAML.

## Updates

The integration creates a Home Assistant update entity. It checks the latest
GitHub release every 30 minutes and can alert when the installed integration is
behind.

The update entity is only an alert. To actually install an update:

1. Open HACS.
2. Open **Ditherloom Suite Home Assistant Add On**.
3. Select **Redownload** or **Download**.
4. Restart Home Assistant.

## MQTT

MQTT is optional.

If the Home Assistant MQTT integration is configured, Ditherloom can publish job
metadata to:

```text
<topic_base>/cmd/job
```

If MQTT is not configured, that publish step is skipped. Direct Wi-Fi Gateway
sending still works while the frame is awake and reachable.

## Troubleshooting

### HACS Says The Repository Already Exists

Close the custom repository dialog. Search HACS for **Ditherloom**, open the
existing entry, then install or redownload from there.

### The Integration Does Not Appear In Add Integration

Confirm all of these:

- The custom repository type was **Integration**.
- HACS says the repository is downloaded.
- Home Assistant was restarted after download.
- This folder exists on the Home Assistant server:

  ```text
  /config/custom_components/ditherloom_suite_ha_addon
  ```

- This file exists:

  ```text
  /config/custom_components/ditherloom_suite_ha_addon/manifest.json
  ```

Then search Add integration for **Ditherloom**.

If it still does not appear, check **Settings > System > Logs** for:

```text
ditherloom_suite_ha_addon
```

### Frame-Awake Delivery Does Not Happen

Confirmed causes to check:

- The frame is asleep.
- The frame is not currently in its Wi-Fi Gateway window.
- The firmware did not post to the `frame-awake` endpoint.
- The `frame-awake` body did not include the frame's live Gateway IP/host.
- The announced Gateway port is wrong.
- Home Assistant and the frame are not on reachable local network paths.
- VPN, VLAN, firewall, or router isolation is blocking the connection.
- The frame firmware does not support the existing Gateway send commands.

### Weather Does Not Render

Check:

- Home Assistant has internet access for Open-Meteo.
- Latitude and longitude are valid.
- The configured location is not `0,0` unless that is intentional.
- Home Assistant logs do not show a Ditherloom integration error.

### Weather Renders But Does Not Reach The Frame

Check:

- The frame is awake on Wi-Fi.
- The frame posted a `frame-awake` event.
- The **Frame handshake status** sensor shows the latest awake event.
- The frame firmware supports the existing Gateway send commands.
- The target slot is valid. The default reserved slot is `445`.

## Remove The Integration

1. In Home Assistant, go to **Settings > Devices & services**.
2. Open **Ditherloom Suite Home Assistant Add On**.
3. Remove the integration entry.
4. Open HACS.
5. Remove the Ditherloom repository if you no longer want it installed.
6. Restart Home Assistant.
