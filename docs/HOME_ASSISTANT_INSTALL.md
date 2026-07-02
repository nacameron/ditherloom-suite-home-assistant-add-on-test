# Installing The Prototype On Home Assistant

Preferred route: install as a custom integration. See:

```text
docs/CUSTOM_INTEGRATION_INSTALL.md
```

The add-on/app route below is kept as a fallback only.

This project now has an installable add-on folder:

```text
addons/ditherloom_suite_ha_addon
```

## Option A: Local Add-On Folder

Use this while testing on your own Home Assistant server.

1. Copy the folder `addons/ditherloom_suite_ha_addon` into the Home Assistant local
   add-ons directory:

   ```text
   /addons/ditherloom_suite_ha_addon
   ```

2. In Home Assistant, open Settings > Add-ons.
3. Open the add-on store.
4. Use the menu to check for updates / reload local add-ons.
5. Install `Ditherloom Suite Home Assistant Add On`.
6. Start it.
7. Open the add-on UI from Home Assistant.

The add-on listens on port `8099`. The frame needs the direct local URL, for
example:

```text
http://homeassistant.local:8099
```

Do not use the Ingress URL for ESP32 payload fetches. Ingress is for the Home
Assistant UI.

## Option B: Repository Later

For easier installation later, publish this project as a Home Assistant add-on
repository. The repo root already contains:

```text
repository.yaml
addons/ditherloom_suite_ha_addon/config.yaml
addons/ditherloom_suite_ha_addon/Dockerfile
```

Then Home Assistant can add the repository URL from the add-on store.

## Current Test Path

1. Open the add-on UI.
2. Use `Open-Meteo Test` with latitude and longitude.
3. Confirm the preview looks good.
4. Set:
   - Library ID
   - frame Wi-Fi host/IP
   - Gateway port, normally `5757`
   - public base URL reachable by the frame
   - optional MQTT topic base, normally `ditherloom/<library_id>`, only if MQTT
     is configured in Home Assistant
5. Publish the weather job.

MQTT is optional. The current custom integration test path can send directly to
the frame through the Wi-Fi Gateway while the frame is awake.

## Runtime Model

The integration must assume the frame is asleep most of the time.

The intended production flow is a repeating update cycle:

1. Ditherloom Suite configures the frame's repeating Home Assistant update wake
   schedule.
2. The frame wakes on that schedule.
3. The frame opens its existing custom Wi-Fi Gateway window.
4. Home Assistant sends one latest queued/rendered update job during that
   window.
5. The frame validates payload length and CRC.
6. The frame displays the content.
7. Home Assistant or firmware requests `IDLE`/`SLEEP`.
8. The frame returns to sleep.
9. The frame re-wakes at the next configured update time and repeats the cycle.

The Home Assistant side should not rely on a permanent Wi-Fi connection or a
required MQTT connection.

## Provider Note

Open-Meteo is used only as the first free/non-commercial weather path. Keep
weather provider selection configurable before wider release.
