# Privacy Notes

Ditherloom Suite Home Assistant Add On is designed to run locally inside Home
Assistant and to render local payloads for a Ditherloom frame.

## Weather Coordinates

When you render or send a weather card, the configured or map-picked latitude
and longitude are sent to Open-Meteo to fetch weather data.

If you do not provide a weather location name, the same latitude and longitude
are also sent to Nominatim/OpenStreetMap for a reverse lookup. This lookup is
used only to choose a human-readable place name for the weather card template,
for example the text shown in the bottom location bar.

The integration does not use the reverse lookup to track you, build a location
history, or send location data to Ditherloom servers. Reverse lookup results are
cached in the Home Assistant process for repeated use of the same coordinates.

## Local Frame Delivery

Rendered weather payloads are stored locally by Home Assistant and served to the
frame through the configured local Home Assistant/Gateway path. The payload is a
packed display image, not the original Home Assistant configuration.

## Optional MQTT

MQTT is optional. If MQTT is configured, the integration can publish job metadata
such as command ID, content ID, payload URL, length, CRC32, expiry time, wake
window minutes, and target slot. It does not publish Wi-Fi passwords.
