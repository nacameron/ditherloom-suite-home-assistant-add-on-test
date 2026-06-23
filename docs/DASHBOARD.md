# Ditherloom Home Assistant Dashboard

This integration exposes Home Assistant entities that can be used to build a
small Ditherloom control dashboard:

- `Weather preview` image entity
- `Render weather preview` button
- `Send weather to frame` button
- `Synchronise Wi-Fi wake window` button
- `Last job status` diagnostic sensor
- Ditherloom update entity

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
    columns: 3
    square: false
    cards:
      - type: button
        entity: button.ditherloom_suite_home_assistant_add_on_render_weather_preview
        name: Render
        tap_action:
          action: toggle
      - type: button
        entity: button.ditherloom_suite_home_assistant_add_on_send_weather_to_frame
        name: Send
        tap_action:
          action: toggle
      - type: button
        entity: button.ditherloom_suite_home_assistant_add_on_synchronise_wi_fi_wake_window
        name: Sync
        tap_action:
          action: toggle
  - type: entities
    entities:
      - entity: sensor.ditherloom_suite_home_assistant_add_on_last_job_status
        name: Last job
      - entity: update.ditherloom_suite_home_assistant_add_on_update
        name: Integration update
```

Automatic scheduled sending is not enabled yet. Until that is added, use the
`Send weather to frame` button or the `ditherloom_suite_ha_addon.send_weather_card`
action.
