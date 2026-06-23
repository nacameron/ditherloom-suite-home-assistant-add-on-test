from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_FRAME_HOST,
    CONF_FRAME_PORT,
    CONF_DISPLAY_MODE,
    CONF_LATITUDE,
    CONF_LIBRARY_ID,
    CONF_LOCATION_NAME,
    CONF_LONGITUDE,
    CONF_MAX_JOBS_PER_WAKE,
    CONF_TOPIC_BASE,
    CONF_TARGET_SLOT,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_WAKE_WINDOW_MINUTES,
    DEFAULT_FRAME_PORT,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_MAX_JOBS_PER_WAKE,
    DEFAULT_TARGET_SLOT,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DEFAULT_WAKE_WINDOW_MINUTES,
    DISPLAY_MODE_COLOUR,
    DISPLAY_MODE_MONO,
    DOMAIN,
)


class DitherloomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
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
                vol.Optional(CONF_LATITUDE, default="0"): str,
                vol.Optional(CONF_LONGITUDE, default="0"): str,
                vol.Optional(CONF_UPDATE_INTERVAL_MINUTES, default=DEFAULT_UPDATE_INTERVAL_MINUTES): int,
                vol.Optional(CONF_WAKE_WINDOW_MINUTES, default=DEFAULT_WAKE_WINDOW_MINUTES): int,
                vol.Optional(CONF_MAX_JOBS_PER_WAKE, default=DEFAULT_MAX_JOBS_PER_WAKE): int,
                vol.Optional(CONF_TARGET_SLOT, default=DEFAULT_TARGET_SLOT): int,
                vol.Optional(CONF_DISPLAY_MODE, default=DEFAULT_DISPLAY_MODE): vol.In([DISPLAY_MODE_COLOUR, DISPLAY_MODE_MONO]),
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
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = {**self._entry.data, **self._entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_FRAME_HOST, default=data.get(CONF_FRAME_HOST, "")): str,
                vol.Optional(CONF_FRAME_PORT, default=data.get(CONF_FRAME_PORT, DEFAULT_FRAME_PORT)): int,
                vol.Optional(CONF_TOPIC_BASE, default=data.get(CONF_TOPIC_BASE, "")): str,
                vol.Optional(CONF_LOCATION_NAME, default=data.get(CONF_LOCATION_NAME, "Home")): str,
                vol.Optional(CONF_LATITUDE, default=data.get(CONF_LATITUDE, "0")): str,
                vol.Optional(CONF_LONGITUDE, default=data.get(CONF_LONGITUDE, "0")): str,
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
                vol.Optional(
                    CONF_DISPLAY_MODE,
                    default=data.get(CONF_DISPLAY_MODE, DEFAULT_DISPLAY_MODE),
                ): vol.In([DISPLAY_MODE_COLOUR, DISPLAY_MODE_MONO]),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
