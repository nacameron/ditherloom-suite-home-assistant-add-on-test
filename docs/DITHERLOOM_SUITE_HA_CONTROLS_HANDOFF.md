# Ditherloom Suite Home Assistant Controls Handoff

Audience: Codex or another AI agent adding the Home Assistant setup controls to
the main Ditherloom Suite app.

This document describes only the Ditherloom Suite side. The Home Assistant
runtime is built separately in this repository as a Home Assistant custom
integration, not as a Helper and not as a required Home Assistant App/Add-on.

## Home Assistant Integration Contract

The Home Assistant-side runtime is:

```text
Ditherloom Suite Home Assistant Add On
```

Custom integration domain:

```text
ditherloom_suite_ha_addon
```

Public test repository for HACS custom repository install:

```text
https://github.com/nacameron/ditherloom-suite-home-assistant-add-on-test
```

Home Assistant install path:

```text
HACS custom repository -> category Integration -> restart Home Assistant ->
Settings > Devices & services > Add integration
```

Registered Home Assistant services:

```text
ditherloom_suite_ha_addon.render_weather_card
ditherloom_suite_ha_addon.send_weather_card
```

Default reserved Home Assistant content slot:

```text
445
```

The Ditherloom Suite app should present these details as setup guidance, but it
must not try to install or configure Home Assistant internally.

## Boundary

Ditherloom Suite must only control the Home Assistant integration setup.

It must not:

- render Home Assistant cards,
- choose weather/sensor card content,
- pack Home Assistant payloads,
- publish normal runtime jobs,
- run Home Assistant schedules,
- become a Home Assistant dashboard,
- edit HA card templates,
- manage HA renderer palette settings,
- route Home Assistant through stock firmware, stock USB/BLE, custom USB, or
  custom BLE.

Everything after setup is performed by the Home Assistant server and should be
fairly automatic. The main app may configure when the frame should wake for Home
Assistant, but it must not run the Home Assistant jobs itself.

## Privacy Boundary

Home Assistant integration must not reuse or expose the desktop app's private
gallery/memo library, relink database, source-link paths, encrypted source
cache, or personal source files.

For Home Assistant, the content shown on the frame is generated/rendered by the
user's Home Assistant server and then served or delivered from that Home
Assistant runtime to the frame. Ditherloom Suite is not uploading the user's
personal image files, source folders, or app library contents to the frame for
Home Assistant content.

If Home Assistant is running locally on the user's home network, this is local
LAN traffic between Home Assistant, the local HTTP endpoint or optional
configured broker, and the frame. If the user enables Home Assistant Cloud, a
reverse proxy, remote access, a cloud MQTT broker, or another non-local route,
that is part of the user's Home Assistant/network configuration. It must not be
described as a Ditherloom cloud service, cloud renderer, cloud relay, or
Ditherloom-hosted storage path.

The app UI should phrase this plainly: local Home Assistant stays local; remote
or cloud exposure depends on the user's Home Assistant setup.

## Workflow Chooser

Add a new first-class workflow tile:

```text
Home Assistant
```

The current chooser has four workflows:

```text
Gallery | Memo | Frame Groups | Firmware
```

It is currently a `1 x 4` layout. Change it to a `2 x 3` layout so Home
Assistant appears as its own option, not hidden inside another workflow.

Do not remove or rename the existing workflows. Only change the layout enough to
fit the fifth tile cleanly.

## Transport Rule

The Home Assistant setup workflow is Wi-Fi only.

It applies only when the modified/custom firmware frame is connected through the
custom Wi-Fi Gateway path. It must not expose this setup through:

- stock firmware,
- stock USB,
- stock BLE,
- custom USB,
- custom BLE.

If the selected frame is not a modified/custom firmware Wi-Fi frame, show a
clear unavailable state and a short reason.

## Connected Device Screen

When the device is connected to Wi-Fi and the user opens the Home Assistant
workflow, show setup controls only.

Required sections:

1. Frame identity
   - nickname
   - serial if available
   - Library ID
   - Wi-Fi connected state
   - Gateway state

2. Home Assistant direct Wi-Fi settings
   - Home Assistant base URL reachable from the frame, for example
     `http://homeassistant.local:8123`
   - custom integration domain, display read-only as
     `ditherloom_suite_ha_addon`
   - reserved Home Assistant content slot, default `445`
   - optional MQTT topic base, default `ditherloom/<library_id>`
   - optional broker details only if MQTT support is enabled later:
     broker host or IP, broker port, username, password, discovery prefix

3. Home Assistant scheduled update / wake
   - enable/disable Home Assistant scheduled updates
   - repeating update interval or selected update times
   - wake window length in seconds/minutes
   - maximum jobs per wake, default 1
   - sleep after job completion, default enabled and locked on for normal use
   - sleep after no job is found, default enabled and locked on for normal use
   - next scheduled HA update wake, read back from frame when supported

4. Setup actions
   - test direct Wi-Fi Gateway settings
   - test optional broker settings only when MQTT is enabled/configured
   - write settings to frame
   - read settings from frame
   - publish discovery/setup metadata if supported
   - clear discovery/setup metadata if supported

5. Status
   - last settings write result
   - last settings read result
   - last direct Gateway test result
   - last optional broker test result, only when MQTT is enabled/configured
   - frame HA configured/not configured
   - HA scheduled updates configured/not configured
   - last HA wake time if reported by frame
   - next HA update wake time if reported by frame
   - firmware support missing if the frame does not yet expose the needed
     Gateway commands

6. Home Assistant integration install guidance
   - show whether the user has confirmed the custom integration is installed
   - show the HACS repository URL
   - show the integration name to search in Devices & services
   - show the service names for advanced users
   - show a copyable setup summary:
     - Library ID
     - frame Wi-Fi host/IP
     - Gateway port, default `5757`
     - optional MQTT topic base
     - reserved slot
     - repeating update interval
     - wake window length

## Scheduled Update Wake Requirement

The desired runtime model is:

1. Frame sleeps most of the time.
2. Firmware wakes the frame on the configured repeating Home Assistant update
   schedule.
3. Frame starts the saved Wi-Fi profile and opens the existing custom Wi-Fi
   Gateway window.
4. Home Assistant detects or reaches the awake frame during that bounded window.
5. Home Assistant sends at most the intended latest queued/rendered update job
   for that wake.
6. Frame validates length/CRC, displays the content, and acknowledges the job.
7. Home Assistant or firmware requests `IDLE`/`SLEEP`.
8. Frame returns to low-power sleep.
9. Firmware wakes again at the next configured Home Assistant update time and
   repeats the same bounded update cycle.

The main app setup page must make this lifecycle clear. It should not suggest
that the frame stays online permanently.

The Ditherloom Suite app interface should phrase this as a repeating update
schedule, not a permanent connection:

```text
Wake on schedule -> listen on Wi-Fi -> receive latest Home Assistant update ->
display -> sleep -> re-wake on the next scheduled update.
```

If existing firmware commands already configure timer wake / display schedule /
rotation-style wake behavior for this HA lane, use those existing commands only
if they can safely represent "repeat: wake for Home Assistant update, listen on
Wi-Fi, complete latest job, sleep, then re-wake on the next schedule." If no
existing command can safely represent that without hijacking memo, rotation,
display schedule, or battery maintenance behavior, show a pending firmware
support state instead of misusing those app-owned timer commands.

## Commands

Use Gateway-compatible Wi-Fi setup commands once firmware exposes them. If the
commands do not exist yet, implement the UI as disabled/pending with explicit
firmware support status.

Do not invent a direct non-Gateway protocol.

Expected future command categories:

- read HA settings,
- write HA settings,
- test direct Wi-Fi Gateway settings,
- test optional saved broker settings only if MQTT support is enabled,
- read HA status,
- read HA scheduled update wake,
- write HA scheduled update wake,
- clear HA scheduled update wake,
- publish/clear discovery if handled frame-side.

The exact command names should come from firmware, not from this UI document.

## Existing Command Fallback For First Tests

The Home Assistant custom integration currently has a first-test direct Gateway
path that can use existing Wi-Fi Gateway commands while the frame is already
awake and listening:

```text
PING
BEGIN <slot> <length> <crc32>
B64WRITE <slot> <offset> <base64>
END <slot>
DISPLAY <slot>
IDLE
```

The main app should still configure the frame-side scheduled wake and settings
when firmware supports that. It should not rely on the user manually keeping the
frame awake as the final product behavior.

The first-test path must use the reserved Home Assistant slot, default `445`,
not a normal gallery/memo slot.

## Main App Does Not Own These

The Ditherloom Suite Home Assistant workflow must not control:

- Open-Meteo details,
- selected weather fields,
- sensor card templates,
- palette recipes,
- renderer visuals,
- `.ppbin` generation,
- optional MQTT runtime jobs,
- ack/error runtime dashboard,
- Home Assistant automations,
- sleep-aware job retries.

Ditherloom Suite may configure the frame's repeating HA update wake schedule,
because that is frame setup. It must not decide which weather/sensor card to
render during those wake windows.

Those live in the Home Assistant custom integration/runtime.

## UI Language

The screen should feel like a setup page, not a gallery or dashboard. It should
make the Wi-Fi-only requirement obvious and keep the user focused on connecting
the frame to Home Assistant.

Suggested primary action:

```text
Save Home Assistant Settings To Frame
```

Suggested secondary actions:

```text
Read From Frame
Test Direct Gateway
Show Home Assistant Integration Install Steps
Clear Discovery
```

Avoid calling the Home Assistant custom integration a Helper. It is not a
Helper, because it runs renderer code, caches payloads for Gateway delivery, exposes services, and
talks to the frame.
