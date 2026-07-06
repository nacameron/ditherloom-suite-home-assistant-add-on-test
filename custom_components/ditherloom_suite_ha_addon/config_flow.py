from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    COMICS_SLOT_MODE_ALTERNATE,
    COMICS_SLOT_MODE_PER_SOURCE,
    CONF_ASTROLOGY_ENABLED,
    CONF_ASTROLOGY_SIGNS,
    CONF_COMICS_ENABLED,
    CONF_COMICS_SLOT_MODE,
    CONF_DIESEL_SWEETIES_ENABLED,
    CONF_FRAME_HOST,
    CONF_FRAME_PORT,
    CONF_DISPLAY_MODE,
    CONF_LATITUDE,
    CONF_LIBRARY_ID,
    CONF_LOCATION_NAME,
    CONF_LONGITUDE,
    CONF_MAX_JOBS_PER_WAKE,
    CONF_MOON_ENABLED,
    CONF_MIMI_EUNICE_ENABLED,
    CONF_SUN_ENABLED,
    CONF_TOPIC_BASE,
    CONF_TEMPERATURE_UNIT,
    CONF_WAKE_WINDOW_MINUTES,
    CONF_WEATHER_7_DAY_ENABLED,
    CONF_WEATHER_ENABLED,
    CONF_WEATHER_TODAY_TOMORROW_ENABLED,
    CONF_WIND_SPEED_UNIT,
    CONF_XKCD_ENABLED,
    CONF_XKCD_ATTRIBUTION_NOTICE,
    CONF_XKCD_MODE,
    CONF_XKCD_NUMBER,
    CONF_XKCD_RANDOM_ATTEMPTS,
    DEFAULT_XKCD_MODE,
    DEFAULT_XKCD_RANDOM_ATTEMPTS,
    DEFAULT_COMICS_SLOT_MODE,
    DEFAULT_FRAME_PORT,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_MAX_JOBS_PER_WAKE,
    DEFAULT_TEMPERATURE_UNIT,
    DEFAULT_WAKE_WINDOW_MINUTES,
    DEFAULT_WIND_SPEED_UNIT,
    DISPLAY_MODE_COLOUR,
    DISPLAY_MODE_MONO,
    DOMAIN,
    INTEGRATION_VERSION,
    CONF_WEATHER_LOCATION,
    TEMPERATURE_UNIT_CELSIUS,
    TEMPERATURE_UNIT_FAHRENHEIT,
    WIND_SPEED_UNIT_KMH,
    WIND_SPEED_UNIT_MPH,
    XKCD_MODE_FIXED,
    XKCD_MODE_LATEST,
    XKCD_MODE_RANDOM,
)
from .comics_registry import comics_framework_attributes
from .ha_lane import sanitize_provider_options
from .astrology_provider import SIGN_NAMES, SIGN_ORDER

XKCD_FORM_ENABLED = "Enable xkcd Comic"
XKCD_FORM_ATTRIBUTION = "Attribution - xkcd / Randall Munroe | CC BY-NC 2.5"
XKCD_FORM_MODE = "Comic selection"
XKCD_FORM_NUMBER = "Fixed comic number"
XKCD_FORM_ATTEMPTS = "Random search attempts"
DIESEL_SWEETIES_FORM_ENABLED = "Enable Diesel Sweeties"
MIMI_EUNICE_FORM_ENABLED = "Enable Mimi & Eunice"


class DitherloomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        schema = vol.Schema(
            {
                vol.Required(CONF_LIBRARY_ID): str,
                vol.Required(CONF_FRAME_HOST): str,
                vol.Optional(CONF_FRAME_PORT, default=DEFAULT_FRAME_PORT): int,
                vol.Optional(CONF_TOPIC_BASE): str,
                vol.Optional(CONF_LOCATION_NAME, default="Home"): str,
                vol.Optional(
                    CONF_WEATHER_LOCATION,
                    default=_default_location(
                        self.hass.config.latitude,
                        self.hass.config.longitude,
                        self.hass.config.latitude,
                        self.hass.config.longitude,
                    ),
                ): selector.LocationSelector({"radius": True}),
                vol.Optional(CONF_LATITUDE, default="0"): str,
                vol.Optional(CONF_LONGITUDE, default="0"): str,
                vol.Optional(CONF_WEATHER_ENABLED, default=True): bool,
                vol.Optional(CONF_SUN_ENABLED, default=False): bool,
                vol.Optional(CONF_MOON_ENABLED, default=False): bool,
                vol.Optional(CONF_XKCD_ENABLED, default=False): bool,
                vol.Optional(CONF_XKCD_MODE, default=DEFAULT_XKCD_MODE): _xkcd_mode_selector(),
                vol.Optional(CONF_XKCD_NUMBER): int,
                vol.Optional(CONF_XKCD_RANDOM_ATTEMPTS, default=DEFAULT_XKCD_RANDOM_ATTEMPTS): int,
                vol.Optional(CONF_WAKE_WINDOW_MINUTES, default=DEFAULT_WAKE_WINDOW_MINUTES): int,
                vol.Optional(CONF_MAX_JOBS_PER_WAKE, default=DEFAULT_MAX_JOBS_PER_WAKE): int,
                vol.Optional(CONF_DISPLAY_MODE, default=DEFAULT_DISPLAY_MODE): vol.In([DISPLAY_MODE_COLOUR, DISPLAY_MODE_MONO]),
                vol.Optional(CONF_TEMPERATURE_UNIT, default=DEFAULT_TEMPERATURE_UNIT): vol.In(
                    [TEMPERATURE_UNIT_CELSIUS, TEMPERATURE_UNIT_FAHRENHEIT]
                ),
                vol.Optional(CONF_WIND_SPEED_UNIT, default=DEFAULT_WIND_SPEED_UNIT): vol.In([WIND_SPEED_UNIT_KMH, WIND_SPEED_UNIT_MPH]),
            }
        )
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

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={"ha_lane_error": ""},
        )

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
            menu_options=["weather", "sun", "moon", "comics_framework", "astrology", "device"],
        )

    async def async_step_weather(self, user_input: dict[str, Any] | None = None):
        return self.async_show_menu(
            step_id="weather",
            menu_options=[
                "weather_current",
                "weather_today_tomorrow",
                "weather_7_day",
            ],
        )

    async def async_step_weather_current(self, user_input: dict[str, Any] | None = None):
        data = self._data()
        normalized = sanitize_provider_options(data)
        schema = vol.Schema(
            {
                vol.Optional(CONF_WEATHER_ENABLED, default=_bool_option(normalized, CONF_WEATHER_ENABLED, True)): bool,
                vol.Optional(CONF_LOCATION_NAME, default=data.get(CONF_LOCATION_NAME, "Home")): str,
                vol.Optional(
                    CONF_WEATHER_LOCATION,
                    default=_default_location(
                        data.get(CONF_LATITUDE),
                        data.get(CONF_LONGITUDE),
                        self.hass.config.latitude,
                        self.hass.config.longitude,
                    ),
                ): selector.LocationSelector({"radius": True}),
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
        if user_input is not None:
            return self._save_options_or_show("weather_current", user_input, schema)
        return self.async_show_form(step_id="weather_current", data_schema=schema)

    async def async_step_weather_today_tomorrow(self, user_input: dict[str, Any] | None = None):
        data = self._data()
        schema = self._shared_weather_schema(data, CONF_WEATHER_TODAY_TOMORROW_ENABLED)
        if user_input is not None:
            internal_input = {
                CONF_WEATHER_TODAY_TOMORROW_ENABLED: bool(user_input.get(CONF_WEATHER_TODAY_TOMORROW_ENABLED, False)),
                **_weather_shared_options(user_input),
            }
            return self._save_options_or_show("weather_today_tomorrow", internal_input, schema)
        return self.async_show_form(step_id="weather_today_tomorrow", data_schema=schema)

    async def async_step_weather_7_day(self, user_input: dict[str, Any] | None = None):
        data = self._data()
        schema = self._shared_weather_schema(data, CONF_WEATHER_7_DAY_ENABLED)
        if user_input is not None:
            internal_input = {
                CONF_WEATHER_7_DAY_ENABLED: bool(user_input.get(CONF_WEATHER_7_DAY_ENABLED, False)),
                **_weather_shared_options(user_input),
            }
            return self._save_options_or_show("weather_7_day", internal_input, schema)
        return self.async_show_form(step_id="weather_7_day", data_schema=schema)

    async def async_step_sun(self, user_input: dict[str, Any] | None = None):
        data = self._data()
        schema = vol.Schema(
            {
                vol.Optional(CONF_SUN_ENABLED, default=_bool_option(data, CONF_SUN_ENABLED, False)): bool,
                vol.Optional(CONF_LOCATION_NAME, default=data.get(CONF_LOCATION_NAME, "Home")): str,
                vol.Optional(
                    CONF_WEATHER_LOCATION,
                    default=_default_location(
                        data.get(CONF_LATITUDE),
                        data.get(CONF_LONGITUDE),
                        self.hass.config.latitude,
                        self.hass.config.longitude,
                    ),
                ): selector.LocationSelector({"radius": True}),
                vol.Optional(CONF_LATITUDE, default=data.get(CONF_LATITUDE, "0")): str,
                vol.Optional(CONF_LONGITUDE, default=data.get(CONF_LONGITUDE, "0")): str,
            }
        )
        if user_input is not None:
            return self._save_options_or_show("sun", user_input, schema)
        return self.async_show_form(step_id="sun", data_schema=schema)

    async def async_step_moon(self, user_input: dict[str, Any] | None = None):
        data = self._data()
        schema = vol.Schema(
            {
                vol.Optional(CONF_MOON_ENABLED, default=_bool_option(data, CONF_MOON_ENABLED, False)): bool,
                vol.Optional(CONF_LOCATION_NAME, default=data.get(CONF_LOCATION_NAME, "Home")): str,
                vol.Optional(
                    CONF_WEATHER_LOCATION,
                    default=_default_location(
                        data.get(CONF_LATITUDE),
                        data.get(CONF_LONGITUDE),
                        self.hass.config.latitude,
                        self.hass.config.longitude,
                    ),
                ): selector.LocationSelector({"radius": True}),
                vol.Optional(CONF_LATITUDE, default=data.get(CONF_LATITUDE, "0")): str,
                vol.Optional(CONF_LONGITUDE, default=data.get(CONF_LONGITUDE, "0")): str,
            }
        )
        if user_input is not None:
            return self._save_options_or_show("moon", user_input, schema)
        return self.async_show_form(step_id="moon", data_schema=schema)

    async def async_step_comics_framework(self, user_input: dict[str, Any] | None = None):
        return self.async_show_menu(
            step_id="comics_framework",
            menu_options=[
                "comics_settings",
                "comics_xkcd",
                "comics_diesel_sweeties",
                "comics_mimi_eunice",
            ],
        )

    async def async_step_comics_settings(self, user_input: dict[str, Any] | None = None):
        data = self._data()
        schema = vol.Schema(
            {
                vol.Optional(CONF_COMICS_ENABLED, default=_bool_option(data, CONF_COMICS_ENABLED, False)): bool,
                vol.Optional(
                    CONF_COMICS_SLOT_MODE,
                    default=data.get(CONF_COMICS_SLOT_MODE, DEFAULT_COMICS_SLOT_MODE),
                ): _comics_slot_mode_selector(),
            }
        )
        if user_input is not None:
            return self._save_options_or_show("comics_settings", user_input, schema)
        return self.async_show_form(
            step_id="comics_settings",
            data_schema=schema,
            description_placeholders=self._comics_description_placeholders(data),
        )

    async def async_step_comics(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_comics_framework(user_input)

    async def async_step_comics_xkcd(self, user_input: dict[str, Any] | None = None):
        data = self._data()
        schema = vol.Schema(
            {
                vol.Optional(XKCD_FORM_ENABLED, default=_bool_option(data, CONF_XKCD_ENABLED, False)): bool,
                vol.Optional(
                    XKCD_FORM_ATTRIBUTION,
                    default="xkcd / Randall Munroe | CC BY-NC 2.5",
                ): _xkcd_attribution_selector(),
                vol.Optional(XKCD_FORM_MODE, default=data.get(CONF_XKCD_MODE, DEFAULT_XKCD_MODE)): _xkcd_mode_selector(),
                vol.Optional(XKCD_FORM_NUMBER, default=_xkcd_number_text(data.get(CONF_XKCD_NUMBER))): str,
                vol.Optional(
                    XKCD_FORM_ATTEMPTS,
                    default=data.get(CONF_XKCD_RANDOM_ATTEMPTS, DEFAULT_XKCD_RANDOM_ATTEMPTS),
                ): int,
            }
        )
        if user_input is not None:
            internal_input = _xkcd_form_to_options(user_input)
            raw_number = str(user_input.get(XKCD_FORM_NUMBER) or "").strip()
            if raw_number and CONF_XKCD_NUMBER not in internal_input:
                return self.async_show_form(
                    step_id="comics_xkcd",
                    data_schema=schema,
                    errors={XKCD_FORM_NUMBER: "xkcd_number_invalid"},
                    description_placeholders=self._comics_description_placeholders(data),
                )
            if internal_input.get(CONF_XKCD_MODE) == XKCD_MODE_FIXED and not internal_input.get(CONF_XKCD_NUMBER):
                return self.async_show_form(
                    step_id="comics_xkcd",
                    data_schema=schema,
                    errors={XKCD_FORM_NUMBER: "xkcd_number_required"},
                    description_placeholders=self._comics_description_placeholders(data),
                )
            return self._save_options_or_show("comics_xkcd", internal_input, schema)
        return self.async_show_form(
            step_id="comics_xkcd",
            data_schema=schema,
            description_placeholders=self._comics_description_placeholders(data),
        )

    async def async_step_xkcd(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_comics_xkcd(user_input)

    async def async_step_comics_diesel_sweeties(self, user_input: dict[str, Any] | None = None):
        return self._comic_provider_form(
            "comics_diesel_sweeties",
            DIESEL_SWEETIES_FORM_ENABLED,
            CONF_DIESEL_SWEETIES_ENABLED,
            user_input,
        )

    async def async_step_comics_mimi_eunice(self, user_input: dict[str, Any] | None = None):
        return self._comic_provider_form(
            "comics_mimi_eunice",
            MIMI_EUNICE_FORM_ENABLED,
            CONF_MIMI_EUNICE_ENABLED,
            user_input,
        )

    async def async_step_astrology(self, user_input: dict[str, Any] | None = None):
        data = self._data()
        schema = vol.Schema(
            {
                vol.Optional(CONF_ASTROLOGY_ENABLED, default=_bool_option(data, CONF_ASTROLOGY_ENABLED, False)): bool,
                vol.Optional(
                    CONF_ASTROLOGY_SIGNS,
                    default=_selected_astrology_signs(data),
                ): _astrology_sign_selector(),
            }
        )
        if user_input is not None:
            normalized = {
                CONF_ASTROLOGY_ENABLED: bool(user_input.get(CONF_ASTROLOGY_ENABLED, False)),
                CONF_ASTROLOGY_SIGNS: _selected_astrology_signs(user_input),
            }
            return self._save_options_or_show("astrology", normalized, schema)
        return self.async_show_form(step_id="astrology", data_schema=schema)

    async def async_step_device(self, user_input: dict[str, Any] | None = None):
        data = {**self._entry.data, **self._entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_FRAME_HOST, default=data.get(CONF_FRAME_HOST, "")): str,
                vol.Optional(CONF_FRAME_PORT, default=data.get(CONF_FRAME_PORT, DEFAULT_FRAME_PORT)): int,
                vol.Optional(CONF_TOPIC_BASE, default=data.get(CONF_TOPIC_BASE, "")): str,
                vol.Optional(
                    CONF_WAKE_WINDOW_MINUTES,
                    default=data.get(CONF_WAKE_WINDOW_MINUTES, DEFAULT_WAKE_WINDOW_MINUTES),
                ): int,
                vol.Optional(
                    CONF_MAX_JOBS_PER_WAKE,
                    default=data.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE),
                ): int,
            }
        )
        if user_input is not None:
            return self._save_options_or_show("device", user_input, schema)
        return self.async_show_form(
            step_id="device",
            data_schema=schema,
            description_placeholders={"ha_lane_error": ""},
        )

    def _data(self) -> dict[str, Any]:
        return {**self._entry.data, **self._entry.options}

    def _save_options(self, user_input: dict[str, Any]):
        data = {**self._entry.options}
        _apply_picked_location(user_input)
        data.update(user_input)
        data = sanitize_provider_options(data)
        return self.async_create_entry(title="", data=data)

    def _save_options_or_show(self, step_id: str, user_input: dict[str, Any], schema: vol.Schema):
        _apply_picked_location(user_input)
        return self._save_options(user_input)

    def _comic_provider_form(
        self,
        step_id: str,
        form_key: str,
        option_key: str,
        user_input: dict[str, Any] | None,
    ):
        data = self._data()
        schema = vol.Schema(
            {
                vol.Optional(form_key, default=_bool_option(data, option_key, False)): bool,
            }
        )
        if user_input is not None:
            internal_input = {option_key: bool(user_input.get(form_key, False))}
            return self._save_options_or_show(step_id, internal_input, schema)
        return self.async_show_form(
            step_id=step_id,
            data_schema=schema,
            description_placeholders=self._comics_description_placeholders(data),
        )

    def _shared_weather_schema(self, data: dict[str, Any], option_key: str) -> vol.Schema:
        return vol.Schema(
            {
                vol.Optional(option_key, default=_bool_option(data, option_key, False)): bool,
                vol.Optional(CONF_LOCATION_NAME, default=data.get(CONF_LOCATION_NAME, "Home")): str,
                vol.Optional(
                    CONF_WEATHER_LOCATION,
                    default=_default_location(
                        data.get(CONF_LATITUDE),
                        data.get(CONF_LONGITUDE),
                        self.hass.config.latitude,
                        self.hass.config.longitude,
                    ),
                ): selector.LocationSelector({"radius": True}),
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

    def _comics_description_placeholders(self, data: dict[str, Any]) -> dict[str, str]:
        return {
            **_comics_description_placeholders(data),
            **_comic_sample_placeholders(self._entry.entry_id),
        }


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


def _weather_shared_options(user_input: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        CONF_LOCATION_NAME,
        CONF_WEATHER_LOCATION,
        CONF_LATITUDE,
        CONF_LONGITUDE,
        CONF_DISPLAY_MODE,
        CONF_TEMPERATURE_UNIT,
        CONF_WIND_SPEED_UNIT,
    }
    return {key: value for key, value in user_input.items() if key in allowed}


def _default_location(latitude: Any, longitude: Any, fallback_latitude: Any, fallback_longitude: Any) -> dict[str, float]:
    lat = _float_or_zero(latitude)
    lon = _float_or_zero(longitude)
    if lat == 0.0 and lon == 0.0:
        lat = _float_or_zero(fallback_latitude)
        lon = _float_or_zero(fallback_longitude)
    return {
        CONF_LATITUDE: lat,
        CONF_LONGITUDE: lon,
        "radius": 1.0,
    }


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _bool_option(data: dict[str, Any], key: str, default: bool) -> bool:
    return bool(data[key]) if key in data else default


def _xkcd_form_to_options(user_input: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {
        CONF_XKCD_ENABLED: bool(user_input.get(XKCD_FORM_ENABLED, False)),
        CONF_XKCD_MODE: user_input.get(XKCD_FORM_MODE, DEFAULT_XKCD_MODE),
        CONF_XKCD_RANDOM_ATTEMPTS: user_input.get(XKCD_FORM_ATTEMPTS, DEFAULT_XKCD_RANDOM_ATTEMPTS),
    }
    number = _positive_int_or_none(user_input.get(XKCD_FORM_NUMBER))
    if number is not None:
        data[CONF_XKCD_NUMBER] = number
    return data


def _comics_form_to_options(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_COMICS_ENABLED: bool(user_input.get(CONF_COMICS_ENABLED, False)),
        CONF_COMICS_SLOT_MODE: user_input.get(CONF_COMICS_SLOT_MODE, DEFAULT_COMICS_SLOT_MODE),
        **_xkcd_form_to_options(user_input),
    }


def _xkcd_number_text(value: Any) -> str:
    number = _positive_int_or_none(value)
    return "" if number is None else str(number)


def _positive_int_or_none(value: Any) -> int | None:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _xkcd_mode_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {"value": XKCD_MODE_RANDOM, "label": "Random suitable comic"},
                {"value": XKCD_MODE_LATEST, "label": "Latest comic if suitable"},
                {"value": XKCD_MODE_FIXED, "label": "Fixed comic number"},
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _comics_slot_mode_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {"value": COMICS_SLOT_MODE_ALTERNATE, "label": "Alternate enabled comics in one HA slot"},
                {"value": COMICS_SLOT_MODE_PER_SOURCE, "label": "One HA slot per enabled comic"},
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _astrology_sign_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[{"value": sign, "label": SIGN_NAMES[sign]} for sign in SIGN_ORDER],
            mode=selector.SelectSelectorMode.DROPDOWN,
            multiple=True,
        )
    )


def _selected_astrology_signs(data: dict[str, Any]) -> list[str]:
    raw = data.get(CONF_ASTROLOGY_SIGNS)
    if isinstance(raw, str):
        values = [part.strip().lower() for part in raw.replace(";", ",").split(",")]
    elif isinstance(raw, (list, tuple, set)):
        values = [str(part).strip().lower() for part in raw]
    else:
        values = []
    signs = [sign for sign in SIGN_ORDER if sign in set(values)]
    return signs or ["aries"]


def _xkcd_attribution_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {
                    "value": "xkcd / Randall Munroe | CC BY-NC 2.5",
                    "label": "xkcd / Randall Munroe | CC BY-NC 2.5",
                }
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _comic_source_summary(data: dict[str, Any]) -> str:
    sources = comics_framework_attributes(data)["available_comic_sources"]
    names = [str(source["name"]) for source in sources if source.get("implemented")]
    if not names:
        return "No comic sources are implemented yet."
    return ", ".join(names)


def _comic_framework_status(data: dict[str, Any]) -> str:
    attrs = comics_framework_attributes(data)
    if attrs["comics_enabled"]:
        return "Comics framework enabled. xkcd settings are managed inside Comics and still use the xkcd_comic delivery provider."
    return "Comics framework is disabled. xkcd settings are still managed inside Comics and still use the xkcd_comic delivery provider."


def _comics_description_placeholders(data: dict[str, Any]) -> dict[str, str]:
    return {
        "comics_sources": _comic_source_summary(data),
        "comics_status": _comic_framework_status(data),
        "xkcd_attribution": "xkcd / Randall Munroe | CC BY-NC 2.5",
        "xkcd_license_url": "https://xkcd.com/license.html",
    }


def _comic_sample_placeholders(entry_id: str) -> dict[str, str]:
    return {
        "xkcd_sample_image": _comic_sample_markdown(entry_id, "xkcd", "xkcd Comic"),
        "diesel_sweeties_sample_image": _comic_sample_markdown(entry_id, "diesel_sweeties", "Diesel Sweeties"),
        "mimi_eunice_sample_image": _comic_sample_markdown(entry_id, "mimi_eunice", "Mimi & Eunice"),
    }


def _comic_sample_markdown(entry_id: str, sample_id: str, label: str) -> str:
    path = f"/api/ditherloom/{entry_id}/comic-samples/{sample_id}.preview.png?v={INTEGRATION_VERSION}"
    return f"![{label} Ditherloom sample]({path}) [Open sample]({path})"
