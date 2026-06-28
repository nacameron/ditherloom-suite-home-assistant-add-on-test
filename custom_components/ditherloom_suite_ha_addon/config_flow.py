from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_FRAME_HOST,
    CONF_FRAME_PORT,
    CONF_HA_SLOT_POOL,
    CONF_DISPLAY_MODE,
    CONF_DISPLAY_ROTATION_ENABLED,
    CONF_DISPLAY_ROTATION_HOURS,
    CONF_DISPLAY_ROTATION_MINUTES,
    CONF_LATITUDE,
    CONF_LIBRARY_ID,
    CONF_LOCATION_NAME,
    CONF_LONGITUDE,
    CONF_MAX_JOBS_PER_WAKE,
    CONF_MOON_ENABLED,
    CONF_SUN_ENABLED,
    CONF_TOPIC_BASE,
    CONF_TARGET_SLOT,
    CONF_TEMPERATURE_UNIT,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_WAKE_WINDOW_MINUTES,
    CONF_WEATHER_ENABLED,
    CONF_WIND_SPEED_UNIT,
    DEFAULT_FRAME_PORT,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_DISPLAY_ROTATION_HOURS,
    DEFAULT_DISPLAY_ROTATION_MINUTES,
    DEFAULT_MAX_JOBS_PER_WAKE,
    DEFAULT_TARGET_SLOT,
    DEFAULT_TEMPERATURE_UNIT,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DEFAULT_WAKE_WINDOW_MINUTES,
    DEFAULT_WIND_SPEED_UNIT,
    DISPLAY_MODE_COLOUR,
    DISPLAY_MODE_MONO,
    DOMAIN,
    CONF_WEATHER_LOCATION,
    TEMPERATURE_UNIT_CELSIUS,
    TEMPERATURE_UNIT_FAHRENHEIT,
    WIND_SPEED_UNIT_KMH,
    WIND_SPEED_UNIT_MPH,
)


class DitherloomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            _apply_picked_location(user_input)
            library_id = user_input[CONF_LIBRARY_ID].strip()
            await self.async_set_unique_id(library_id)
            self._abort_if_unique_id_configured()
            user_input[CONF_TOPIC_BASE] = user_input.get(CONF_TOPIC_BASE) or f"ditherloom/{library_id}"
            return self.async_create_entry(
                title=f"Ditherloom {library_id}",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_LIBRARY_ID): str,
                vol.Required(CONF_FRAME_HOST): str,
                vol.Optional(CONF_FRAME_PORT, default=DEFAULT_FRAME_PORT): int,
                vol.Optional(CONF_TOPIC_BASE): str,
                vol.Optional(CONF_LOCATION_NAME, default="Home"): str,
                vol.Optional(CONF_WEATHER_LOCATION, default=_default_location(self.hass.config.latitude, self.hass.config.longitude)): selector.LocationSelector(),
                vol.Optional(CONF_LATITUDE, default="0"): str,
                vol.Optional(CONF_LONGITUDE, default="0"): str,
                vol.Optional(CONF_WEATHER_ENABLED, default=True): bool,
                vol.Optional(CONF_SUN_ENABLED, default=False): bool,
                vol.Optional(CONF_MOON_ENABLED, default=False): bool,
                vol.Optional(CONF_DISPLAY_ROTATION_ENABLED, default=False): bool,
                vol.Optional(CONF_DISPLAY_ROTATION_HOURS, default=DEFAULT_DISPLAY_ROTATION_HOURS): int,
                vol.Optional(CONF_DISPLAY_ROTATION_MINUTES, default=DEFAULT_DISPLAY_ROTATION_MINUTES): int,
                vol.Optional(CONF_UPDATE_INTERVAL_MINUTES, default=DEFAULT_UPDATE_INTERVAL_MINUTES): int,
                vol.Optional(CONF_WAKE_WINDOW_MINUTES, default=DEFAULT_WAKE_WINDOW_MINUTES): int,
                vol.Optional(CONF_MAX_JOBS_PER_WAKE, default=DEFAULT_MAX_JOBS_PER_WAKE): int,
                vol.Optional(CONF_TARGET_SLOT, default=DEFAULT_TARGET_SLOT): int,
                vol.Optional(CONF_HA_SLOT_POOL, default=""): str,
                vol.Optional(CONF_DISPLAY_MODE, default=DEFAULT_DISPLAY_MODE): vol.In([DISPLAY_MODE_COLOUR, DISPLAY_MODE_MONO]),
                vol.Optional(CONF_TEMPERATURE_UNIT, default=DEFAULT_TEMPERATURE_UNIT): vol.In(
                    [TEMPERATURE_UNIT_CELSIUS, TEMPERATURE_UNIT_FAHRENHEIT]
                ),
                vol.Optional(CONF_WIND_SPEED_UNIT, default=DEFAULT_WIND_SPEED_UNIT): vol.In([WIND_SPEED_UNIT_KMH, WIND_SPEED_UNIT_MPH]),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DitherloomOptionsFlow(config_entry)


class DitherloomOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["weather", "sun", "moon", "rotation", "device"],
        )

    async def async_step_weather(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self._save_options(user_input)
        data = self._data()
        schema = vol.Schema(
            {
                vol.Optional(CONF_WEATHER_ENABLED, default=_bool_option(data, CONF_WEATHER_ENABLED, True)): bool,
                vol.Optional(CONF_LOCATION_NAME, default=data.get(CONF_LOCATION_NAME, "Home")): str,
                vol.Optional(
                    CONF_WEATHER_LOCATION,
                    default=_default_location(data.get(CONF_LATITUDE), data.get(CONF_LONGITUDE)),
                ): selector.LocationSelector(),
                vol.Optional(CONF_LATITUDE, default=data.get(CONF_LATITUDE, "0")): str,
                vol.Optional(CONF_LONGITUDE, default=data.get(CONF_LONGITUDE, "0")): str,
                vol.Optional(
                    CONF_DISPLAY_MODE,
                    default=data.get(CONF_DISPLAY_MODE, DEFAULT_DISPLAY_MODE),
                ): vol.In([DISPLAY_MODE_COLOUR, DISPLAY_MODE_MONO]),
                vol.Optional(
                    CONF_TEMPERATURE_UNIT,
                    default=data.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT),
                ): vol.In([TEMPERATURE_UNIT_CELSIUS, TEMPERATURE_UNIT_FAHRENHEIT]),
                vol.Optional(
                    CONF_WIND_SPEED_UNIT,
                    default=data.get(CONF_WIND_SPEED_UNIT, DEFAULT_WIND_SPEED_UNIT),
                ): vol.In([WIND_SPEED_UNIT_KMH, WIND_SPEED_UNIT_MPH]),
            }
        )
        return self.async_show_form(step_id="weather", data_schema=schema)

    async def async_step_sun(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self._save_options(user_input)
        data = self._data()
        schema = vol.Schema(
            {
                vol.Optional(CONF_SUN_ENABLED, default=_bool_option(data, CONF_SUN_ENABLED, False)): bool,
                vol.Optional(CONF_LOCATION_NAME, default=data.get(CONF_LOCATION_NAME, "Home")): str,
                vol.Optional(
                    CONF_WEATHER_LOCATION,
                    default=_default_location(data.get(CONF_LATITUDE), data.get(CONF_LONGITUDE)),
                ): selector.LocationSelector(),
                vol.Optional(CONF_LATITUDE, default=data.get(CONF_LATITUDE, "0")): str,
                vol.Optional(CONF_LONGITUDE, default=data.get(CONF_LONGITUDE, "0")): str,
            }
        )
        return self.async_show_form(step_id="sun", data_schema=schema)

    async def async_step_moon(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self._save_options(user_input)
        data = self._data()
        schema = vol.Schema(
            {
                vol.Optional(CONF_MOON_ENABLED, default=_bool_option(data, CONF_MOON_ENABLED, False)): bool,
                vol.Optional(CONF_LOCATION_NAME, default=data.get(CONF_LOCATION_NAME, "Home")): str,
                vol.Optional(
                    CONF_WEATHER_LOCATION,
                    default=_default_location(data.get(CONF_LATITUDE), data.get(CONF_LONGITUDE)),
                ): selector.LocationSelector(),
                vol.Optional(CONF_LATITUDE, default=data.get(CONF_LATITUDE, "0")): str,
                vol.Optional(CONF_LONGITUDE, default=data.get(CONF_LONGITUDE, "0")): str,
            }
        )
        return self.async_show_form(step_id="moon", data_schema=schema)

    async def async_step_rotation(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self._save_options(user_input)
        data = self._data()
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DISPLAY_ROTATION_ENABLED,
                    default=_bool_option(data, CONF_DISPLAY_ROTATION_ENABLED, False),
                ): bool,
                vol.Optional(
                    CONF_DISPLAY_ROTATION_HOURS,
                    default=data.get(CONF_DISPLAY_ROTATION_HOURS, DEFAULT_DISPLAY_ROTATION_HOURS),
                ): vol.All(int, vol.Range(min=0, max=24)),
                vol.Optional(
                    CONF_DISPLAY_ROTATION_MINUTES,
                    default=data.get(CONF_DISPLAY_ROTATION_MINUTES, DEFAULT_DISPLAY_ROTATION_MINUTES),
                ): vol.All(int, vol.Range(min=0, max=59)),
            }
        )
        return self.async_show_form(step_id="rotation", data_schema=schema)

    async def async_step_device(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self._save_options(user_input)
        data = {**self._entry.data, **self._entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_FRAME_HOST, default=data.get(CONF_FRAME_HOST, "")): str,
                vol.Optional(CONF_FRAME_PORT, default=data.get(CONF_FRAME_PORT, DEFAULT_FRAME_PORT)): int,
                vol.Optional(CONF_TOPIC_BASE, default=data.get(CONF_TOPIC_BASE, "")): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    default=data.get(CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES),
                ): int,
                vol.Optional(
                    CONF_WAKE_WINDOW_MINUTES,
                    default=data.get(CONF_WAKE_WINDOW_MINUTES, DEFAULT_WAKE_WINDOW_MINUTES),
                ): int,
                vol.Optional(
                    CONF_MAX_JOBS_PER_WAKE,
                    default=data.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE),
                ): int,
                vol.Optional(CONF_TARGET_SLOT, default=data.get(CONF_TARGET_SLOT, DEFAULT_TARGET_SLOT)): int,
                vol.Optional(CONF_HA_SLOT_POOL, default=data.get(CONF_HA_SLOT_POOL, "")): str,
            }
        )
        return self.async_show_form(step_id="device", data_schema=schema)

    def _data(self) -> dict[str, Any]:
        return {**self._entry.data, **self._entry.options}

    def _save_options(self, user_input: dict[str, Any]):
        data = {**self._entry.options}
        _apply_picked_location(user_input)
        data.update(user_input)
        return self.async_create_entry(title="", data=data)


def _apply_picked_location(data: dict[str, Any]) -> None:
    picked_location = data.get(CONF_WEATHER_LOCATION)
    if not isinstance(picked_location, dict):
        return
    latitude = picked_location.get(CONF_LATITUDE)
    longitude = picked_location.get(CONF_LONGITUDE)
    if latitude is not None:
        data[CONF_LATITUDE] = str(latitude)
    if longitude is not None:
        data[CONF_LONGITUDE] = str(longitude)


def _default_location(latitude: Any, longitude: Any) -> dict[str, float]:
    return {
        CONF_LATITUDE: _float_or_zero(latitude),
        CONF_LONGITUDE: _float_or_zero(longitude),
    }


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _bool_option(data: dict[str, Any], key: str, default: bool) -> bool:
    return bool(data[key]) if key in data else default
