# Ditherloom Home Assistant Dashboard

This integration exposes Home Assistant entities that can be used to build a
small Ditherloom control dashboard:

- `Weather preview` image entity
- `Render weather preview` button
- `Last job status` diagnostic sensor
- `Frame handshake status` diagnostic sensor
- Ditherloom update entity

Home Assistant refreshes the weather payload on its configured interval. The
frame sends a `frame-awake` callback when it wakes on Wi-Fi, and Home Assistant
then pushes the waiting packed payload through the existing frame Gateway.

Entity IDs are assigned by Home Assistant and can vary by install. Open the
Ditherloom device page after restart, copy the entity IDs, then paste them into
the manual dashboard card below.

## Manual Dashboard Card

In Home Assistant, open the dashboard editor, add a Manual card, and replace the
example entity IDs with the ones from your Ditherloom device.

```yaml
type: vertical-stack
cards:
  - type: heading
    heading: Ditherloom Weather Frame
  - type: picture-entity
    entity: image.ditherloom_suite_home_assistant_add_on_weather_preview
    name: Last rendered preview
    show_state: false
  - type: grid
    columns: 2
    square: false
    cards:
      - type: button
        entity: button.ditherloom_suite_home_assistant_add_on_render_weather_preview
        name: Render
        tap_action:
          action: toggle
  - type: entities
    entities:
      - entity: sensor.ditherloom_suite_home_assistant_add_on_last_job_status
        name: Last job
      - entity: sensor.ditherloom_suite_home_assistant_add_on_frame_handshake_status
        name: Frame handshake
      - entity: update.ditherloom_suite_home_assistant_add_on_update
        name: Integration update
```

Useful diagnostic attributes on **Frame handshake status** include
`weather_refresh_next_at`, `frame_awake_last_received_at`,
`frame_awake_last_success_at`, and `frame_sleeping_last_received_at`.
