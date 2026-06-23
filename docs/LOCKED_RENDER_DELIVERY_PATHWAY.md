# Locked Render Delivery Pathway

This pathway is locked because it has been tested successfully against the Ditherloom frame wake cycle.

All scheduled content types must use this sequence:

1. Pre-render the content before the expected frame wake.
2. Write the 400x300 packed payload to disk using the existing device packer.
3. Publish the job metadata with the same payload URL, CRC, slot, and expiry window.
4. Wait until the expected frame wake anchor.
5. probe the frame gateway before sending.
6. send the existing packed payload only after the gateway answers.
7. Retry gateway probing during the configured drift/search window.
8. schedule the next cycle from the expected wake anchor, not from a failure time or wall-clock now.

Do not render during the frame wake window. Rendering and network lookups must already be complete before the device is expected to be reachable.

Do not create content-specific send paths. Weather, future calendar cards, alerts, sensor dashboards, and other cards must feed into the same pre-render, probe, send-existing-payload pathway.

Do not bypass the gateway probe. A send attempt must only happen after the frame gateway has answered.

Do not schedule the next cycle from a failed attempt time. The cycle must stay aligned to the expected wake anchor so retry delays do not drift the schedule.

Current locked timings:

- Pre-render lead: 30 seconds before expected wake.
- Probe interval: 10 seconds.
- Counter drift search: 300 seconds after the configured wake window.
