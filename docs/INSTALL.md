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
| `Repeating update interval minutes` | Fallback only until the frame timer is synced. |
| `Wake window minutes` | Fallback only until the frame timer is synced. |
| `Max jobs per wake` | Currently `1`. |
| `Target slot` | Reserved frame slot. Default `445`. |
| `Display mode` | `colour` or `mono`. |

The frame owns the real Home Assistant schedule. After setup, use the sync
button to import the firmware-controlled timer values from the frame.

## Sync The Frame Timer

The integration creates a **Synchronise Wi-Fi wake window** button.

Use it when the frame is awake on Wi-Fi:

1. Wake the frame onto Wi-Fi using the Ditherloom firmware workflow.
2. In Home Assistant, open the Ditherloom integration device.
3. Press **Synchronise Wi-Fi wake window**.

The integration connects to the frame Gateway and reads:

- `HACONFIG`
- `SLEEPINFO`

It imports the firmware-owned Home Assistant timer values, including
`intervalMinutes` and `wakeWindowSeconds`.

The sync button reads the frame timer. It does not write a new timer to the
frame and does not keep Wi-Fi permanently alive.

After a successful sync, Home Assistant schedules one automatic weather send for
the next expected firmware wake window. It repeats from the imported
`intervalMinutes` value and uses the imported `wakeWindowSeconds` value as the
retry window if the frame is not reachable on the first attempt.

Home Assistant also creates a persistent notification confirming the sync and
showing the next automatic weather-send time.

The Ditherloom device page also exposes **Frame schedule status**. After sync,
that sensor should show `synced` and include the next automatic send time in its
attributes.

## Test Weather Rendering

After setup:

1. Open the Ditherloom integration device in Home Assistant.
2. Press **Render weather preview**.
3. Check the **Weather preview** image entity.
4. Wake the frame onto Wi-Fi.
5. Press **Send weather to frame**.

Weather data is fetched from Open-Meteo. The optional place-name lookup uses
Nominatim/OpenStreetMap when a map-picked location needs a display name. See
`PRIVACY.md` for location privacy notes.

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

### Sync Button Says The Frame Is Not Reachable

Confirmed causes to check:

- The frame is asleep.
- The frame is not currently in its Wi-Fi Gateway window.
- The configured frame host/IP is wrong.
- The configured Gateway port is wrong.
- Home Assistant and the frame are not on reachable local network paths.
- VPN, VLAN, firewall, or router isolation is blocking the connection.
- The frame firmware does not support `HACONFIG` and `SLEEPINFO`.

### Weather Does Not Render

Check:

- Home Assistant has internet access for Open-Meteo.
- Latitude and longitude are valid.
- The configured location is not `0,0` unless that is intentional.
- Home Assistant logs do not show a Ditherloom integration error.

### Weather Renders But Does Not Reach The Frame

Check:

- The frame is awake on Wi-Fi.
- The frame Gateway responds at the configured host/IP and port.
- The frame firmware supports the existing Gateway send commands.
- The target slot is valid. The default reserved slot is `445`.

## Remove The Integration

1. In Home Assistant, go to **Settings > Devices & services**.
2. Open **Ditherloom Suite Home Assistant Add On**.
3. Remove the integration entry.
4. Open HACS.
5. Remove the Ditherloom repository if you no longer want it installed.
6. Restart Home Assistant.
