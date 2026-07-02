# Locked Render Delivery Pathway

This pathway is locked because the frame wake timing belongs to firmware, not
Home Assistant.

Home Assistant must refresh the weather payload on the Home Assistant interval
and wait for the frame to initiate delivery. When the frame is awake, Home
Assistant must send the existing packed payload rather than render a new one.

All scheduled content types must use this sequence:

1. Home Assistant refreshes the weather payload on the Home Assistant interval.
2. Rendering and weather/network lookups finish before any frame contact.
3. The 400x300 packed payload is written to disk using the existing device packer.
4. Cached job metadata records CRC, slot, packed length, provider identity, and delivery freshness.
5. The frame wakes on its firmware schedule and connects to Wi-Fi.
6. Firmware posts to `/api/ditherloom/<entry_id>/frame-awake` with its live Gateway host, port, and slot.
7. Home Assistant returns the `frame-awake` HTTP response, waits briefly for firmware to return to its single Gateway listener, then sends the existing packed payload through one Gateway session: `PING`, `BEGIN`, `B64WRITE`, `END`, `SETSLOTCLASS <slot> ha`, `SLOTCLASS <slot>`, optional `HAROTATION on <seconds> <slot_csv>`, and mandatory `HACOMPLETE all_jobs_complete`.
8. Firmware may post to `/api/ditherloom/<entry_id>/frame-sleeping` before it returns to deep sleep.

Do not probe for the frame from Home Assistant. The frame wake callback is the
delivery trigger.

Do not render during the frame wake window unless there is no cached payload.
The normal operating state is that a fresh payload is already waiting before
the frame wakes.

Do not create content-specific send paths. Weather, future calendar cards,
alerts, sensor dashboards, and other cards must feed into the same refresh,
frame-awake, send-existing-payload pathway.

Home Assistant may own more than one frame slot. Every HA-rendered slot must be
explicitly assigned to the HA lane before writing:

```text
SETSLOTCLASS <slot> ha
SLOTCLASS <slot>
```

The expected response must confirm `class=ha`, `value=3`, and
`rotation_selectable=0`. The integration must not overwrite image, memo, or
system slots unless those slots are explicitly configured as Home Assistant
slots.

Locked hybrid render conversion:

1. Exact Ditherloom safe template colours are protected and rendered through their locked ordered recipes.
2. Non-exact pixels, including central weather artwork and generated photographic/weather graphics, use the same Atkinson-style four-colour photo conversion family as the main Ditherloom app.
3. The final packer must not globally snap near-safe colours to ordered recipes. Near-safe snapping destroys photo-style artwork and produces visibly incorrect central graphics on the device.

This conversion rule applies to every current and future weather card, not only
the sunny template.
