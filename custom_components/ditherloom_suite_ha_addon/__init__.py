from __future__ import annotations

import asyncio
import base64
import inspect
import json
import logging
import math
import re
import shutil
import socket
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import partial
from pathlib import Path
from typing import Any, Callable

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_point_in_time, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_CONTENT_ID,
    ATTR_CRC32,
    ATTR_LAST_ERROR,
    ATTR_PREVIEW_URL,
    CONF_ASTROLOGY_ENABLED,
    CONF_ASTROLOGY_SIGNS,
    CONF_ASTRONOMY_CONSTELLATION_ENABLED,
    CONF_ASTRONOMY_AURORA_WATCH_ENABLED,
    CONF_ASTRONOMY_CONDITIONS_ENABLED,
    CONF_ASTRONOMY_MOON_WATCH_ENABLED,
    CONF_ASTRONOMY_OVERHEAD_ENABLED,
    CONF_ASTRONOMY_SOLAR_ACTIVITY_ENABLED,
    CONF_ASTRONOMY_TONIGHT_SKY_ENABLED,
    CONF_ASTRONOMY_VISIBLE_PLANETS_ENABLED,
    CONF_DISPLAY_MODE,
    CONF_DISPLAY_ROTATION_ENABLED,
    CONF_DISPLAY_ROTATION_HOURS,
    CONF_DISPLAY_ROTATION_MINUTES,
    CONF_DIESEL_SWEETIES_ENABLED,
    CONF_FRAME_HA_ROTATION_ENABLED,
    CONF_FRAME_HA_ROTATION_SECONDS,
    CONF_FRAME_HA_SLOT_CSV,
    CONF_FRAME_HA_SLOT_POOL,
    CONF_FRAME_HOST,
    CONF_FRAME_INTERVAL_MINUTES,
    CONF_FRAME_PORT,
    CONF_FRAME_RESERVED_SLOT,
    CONF_HA_ROTATION_ENABLED,
    CONF_HA_ROTATION_SECONDS,
    CONF_LATITUDE,
    CONF_LOCATION_NAME,
    CONF_LONGITUDE,
    CONF_MAX_JOBS_PER_WAKE,
    CONF_MOON_ENABLED,
    CONF_MIMI_EUNICE_ENABLED,
    CONF_SUN_ENABLED,
    CONF_TARGET_SLOT,
    CONF_TEMPERATURE_UNIT,
    CONF_TOPIC_BASE,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_WEATHER_LOCATION,
    CONF_WAKE_WINDOW_MINUTES,
    CONF_WAKE_WINDOW_SECONDS,
    CONF_WEATHER_7_DAY_ENABLED,
    CONF_WEATHER_ENABLED,
    CONF_WEATHER_PRECIPITATION_ENABLED,
    CONF_WEATHER_RADAR_ATTRIBUTION,
    CONF_WEATHER_RADAR_ENABLED,
    CONF_WEATHER_RADAR_OPENWEATHER_API_KEY,
    CONF_WEATHER_RADAR_OPENWEATHER_LAYER,
    CONF_WEATHER_RADAR_OPENWEATHER_ZOOM,
    CONF_WEATHER_RADAR_PALETTE,
    CONF_WEATHER_TODAY_TOMORROW_ENABLED,
    CONF_WEATHER_UV_ENABLED,
    CONF_WEATHER_WIND_ENABLED,
    CONF_WIND_SPEED_UNIT,
    CONF_XKCD_ENABLED,
    CONF_XKCD_MODE,
    CONF_XKCD_NUMBER,
    CONF_XKCD_RANDOM_ATTEMPTS,
    DEFAULT_XKCD_MODE,
    DEFAULT_XKCD_RANDOM_ATTEMPTS,
    DEFAULT_FRAME_PORT,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_DISPLAY_ROTATION_HOURS,
    DEFAULT_DISPLAY_ROTATION_MINUTES,
    DEFAULT_MAX_JOBS_PER_WAKE,
    DEFAULT_TARGET_SLOT,
    DEFAULT_TEMPERATURE_UNIT,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DEFAULT_WAKE_WINDOW_MINUTES,
    DEFAULT_WEATHER_RADAR_PALETTE,
    DEFAULT_WIND_SPEED_UNIT,
    DEFAULT_HA_ROTATION_SECONDS,
    DEVICE_PACKED_PAYLOAD_BYTES,
    DEVICE_SLOT_COUNT,
    DEVICE_WIFI_B64WRITE_CHUNK_BYTES,
    DEVICE_WIFI_COMMAND_MAX_CHARS,
    DOMAIN,
    INTEGRATION_VERSION,
    SERVICE_RENDER_MOON,
    SERVICE_RENDER_SUN,
    SERVICE_RENDER_WEATHER,
    SERVICE_RENDER_XKCD,
    SERVICE_RENDER_ASTROLOGY,
    SERVICE_SEND_MOON,
    SERVICE_SEND_SUN,
    SERVICE_SEND_WEATHER,
    SERVICE_SEND_XKCD,
    SERVICE_SEND_ASTROLOGY,
    XKCD_MODE_FIXED,
    XKCD_MODE_LATEST,
    XKCD_MODE_RANDOM,
)
from .ha_lane import active_provider_slots, enabled_content_providers, ha_lane_slots, parse_slot_pool, provider_slot_map, slot_csv, validate_ha_lane

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "update", "button", "image"]
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.payloads"
CARD_RENDERER_VERSION = "luxe-0.1.118-radar-basemap-layer"
PROVIDER_WEATHER = "open_meteo_weather"
PROVIDER_WEATHER_TODAY_TOMORROW = "open_meteo_today_tomorrow"
PROVIDER_WEATHER_7_DAY = "open_meteo_7_day_forecast"
PROVIDER_WEATHER_RADAR = "weather_radar"
PROVIDER_WEATHER_PRECIPITATION = "open_meteo_precipitation"
PROVIDER_WEATHER_UV = "open_meteo_uv"
PROVIDER_WEATHER_WIND = "open_meteo_wind"
WEATHER_PROVIDER_IDS = {
    PROVIDER_WEATHER,
    PROVIDER_WEATHER_TODAY_TOMORROW,
    PROVIDER_WEATHER_7_DAY,
    PROVIDER_WEATHER_RADAR,
    PROVIDER_WEATHER_PRECIPITATION,
    PROVIDER_WEATHER_UV,
    PROVIDER_WEATHER_WIND,
}
PROVIDER_SUN = "sunrise_sunset"
PROVIDER_MOON = "moon_phase"
PROVIDER_XKCD = "xkcd_comic"
PROVIDER_DIESEL_SWEETIES = "diesel_sweeties"
PROVIDER_MIMI_EUNICE = "mimi_eunice"
PROVIDER_ASTROLOGY = "daily_astrology"
PROVIDER_ASTRONOMY_VISIBLE_PLANETS = "astronomy_visible_planets"
PROVIDER_ASTRONOMY_MOON_WATCH = "astronomy_moon_watch"
PROVIDER_ASTRONOMY_CONSTELLATION = "astronomy_constellation"
PROVIDER_ASTRONOMY_TONIGHT_SKY = "astronomy_tonight_sky"
PROVIDER_ASTRONOMY_OVERHEAD = "astronomy_overhead"
PROVIDER_ASTRONOMY_CONDITIONS = "astronomy_conditions"
PROVIDER_ASTRONOMY_SOLAR_ACTIVITY = "astronomy_solar_activity"
PROVIDER_ASTRONOMY_AURORA_WATCH = "astronomy_aurora_watch"
ASTRONOMY_PROVIDER_IDS = {
    PROVIDER_ASTRONOMY_VISIBLE_PLANETS,
    PROVIDER_ASTRONOMY_MOON_WATCH,
    PROVIDER_ASTRONOMY_CONSTELLATION,
    PROVIDER_ASTRONOMY_TONIGHT_SKY,
    PROVIDER_ASTRONOMY_OVERHEAD,
    PROVIDER_ASTRONOMY_CONDITIONS,
    PROVIDER_ASTRONOMY_SOLAR_ACTIVITY,
    PROVIDER_ASTRONOMY_AURORA_WATCH,
}
COMIC_SUCCESSOR_PROVIDERS = {PROVIDER_XKCD, PROVIDER_DIESEL_SWEETIES, PROVIDER_MIMI_EUNICE}
DISCOVERY_AUTH_MESSAGE = "Provide a Home Assistant Long-Lived Access Token."
STALE_FRONTEND_ENTITY_NAMES = {
    "Synchronise Wi-Fi " + "wake window",
    "Send weather " + "to frame",
    "Frame schedule " + "status",
}
PRESERVED_RUNTIME_METADATA_KEYS = (
    "frame_awake",
    "frame_sleeping",
    "frame_awake_last_received_at",
    "frame_awake_last_success_at",
    "frame_awake_last_completion_command",
    "frame_awake_last_completion_sent_at",
    "frame_awake_last_completion_response",
    "frame_awake_last_completion_ok",
    "frame_sleeping_last_received_at",
    "frame_sleeping_expected_after_completion",
    "frame_next_wake_at",
    "frame_content_last_delivered_at",
    "frame_content_last_delivered_count",
    "frame_content_last_delivered_slots",
    "frame_content_last_delivered_crc32",
    "frame_content_last_delivered_content_ids",
    "frame_content_last_delivered_attributions",
    "frame_content_last_delivered_licenses",
    "frame_awake_last_delivered_jobs",
    "frame_awake_last_no_jobs_at",
    "frame_awake_last_no_jobs_host",
    "frame_awake_last_no_jobs_port",
    "frame_awake_last_no_jobs_target_slot",
    "frame_awake_last_no_jobs_providers",
)


def _render_weather_artifact_to_disk(card_data: Any, display_mode: str, payload_dir: Path, stem: str, variant: str = PROVIDER_WEATHER) -> Any:
    from .renderer import (
        render_modern_weather_card,
        render_precipitation_graph_card,
        render_seven_day_weather_card,
        render_to_artifact,
        render_today_tomorrow_weather_card,
        render_uv_graph_card,
        render_weather_radar_card,
        render_wind_graph_card,
    )
    from .renderer.pack import write_artifact

    if variant == PROVIDER_WEATHER_TODAY_TOMORROW:
        image = render_today_tomorrow_weather_card(card_data, colour_mode=display_mode)
        template_name = "weather_today_tomorrow"
    elif variant == PROVIDER_WEATHER_7_DAY:
        image = render_seven_day_weather_card(card_data, colour_mode=display_mode)
        template_name = "weather_7_day_forecast"
    elif variant == PROVIDER_WEATHER_RADAR:
        image = render_weather_radar_card(card_data, colour_mode=display_mode)
        template_name = "weather_radar"
    elif variant == PROVIDER_WEATHER_PRECIPITATION:
        image = render_precipitation_graph_card(card_data, colour_mode=display_mode)
        template_name = "weather_precipitation"
    elif variant == PROVIDER_WEATHER_UV:
        image = render_uv_graph_card(card_data, colour_mode=display_mode)
        template_name = "weather_uv"
    elif variant == PROVIDER_WEATHER_WIND:
        image = render_wind_graph_card(card_data, colour_mode=display_mode)
        template_name = "weather_wind"
    else:
        image = render_modern_weather_card(card_data, colour_mode=display_mode)
        template_name = "weather_current"
    artifact = render_to_artifact(image, template_name, [card_data.source_entity_id])
    write_artifact(artifact, payload_dir, stem)
    return artifact


def _render_sun_artifact_to_disk(provider_data: Any, payload_dir: Path, stem: str) -> tuple[Any, Any]:
    from .renderer import SunCardData, render_sun_card, render_to_artifact
    from .renderer.pack import write_artifact

    card_data = SunCardData(**provider_data.__dict__)
    image = render_sun_card(card_data)
    artifact = render_to_artifact(image, "sunrise_sunset", [card_data.source_entity_id])
    write_artifact(artifact, payload_dir, stem)
    return artifact, card_data


def _render_moon_artifact_to_disk(provider_data: Any, payload_dir: Path, stem: str) -> tuple[Any, Any]:
    from .renderer import MoonCardData, render_moon_card, render_to_artifact
    from .renderer.pack import write_artifact

    card_data = MoonCardData(**provider_data.__dict__)
    image = render_moon_card(card_data)
    artifact = render_to_artifact(image, "moon_phase", [card_data.source_entity_id])
    write_artifact(artifact, payload_dir, stem)
    return artifact, card_data


def _render_xkcd_artifact_to_disk(data: dict[str, Any], payload_dir: Path, stem: str) -> tuple[Any, Any, Any]:
    from .renderer.pack import write_artifact
    from .xkcd_provider import DEFAULT_RANDOM_ATTEMPTS, analyze_xkcd_image, fetch_xkcd_comic, download_comic_image, render_xkcd_card, select_suitable_xkcd

    number = _positive_int(data.get("xkcd_number") or data.get("comic_number") or data.get("number"))
    excluded_numbers = {
        parsed
        for value in data.get("exclude_xkcd_numbers", [])
        if (parsed := _positive_int(value)) is not None
    }
    mode = str(data.get("xkcd_mode") or data.get("mode") or (XKCD_MODE_FIXED if number is not None else XKCD_MODE_RANDOM)).lower()
    if mode == XKCD_MODE_FIXED and number is None:
        raise ValueError("xkcd fixed comic mode needs a comic number.")
    if number is not None:
        if number in excluded_numbers:
            raise ValueError(f"xkcd #{number} was already delivered and is stale for this frame slot.")
        comic = fetch_xkcd_comic(number)
        source = download_comic_image(comic)
        suitability = analyze_xkcd_image(source)
        if not suitability.suitable:
            raise ValueError(f"xkcd #{number} is not suitable for Ditherloom: {', '.join(suitability.reasons)}")
    elif mode == XKCD_MODE_LATEST:
        comic = fetch_xkcd_comic()
        if comic.number in excluded_numbers:
            raise ValueError(f"Latest xkcd #{comic.number} was already delivered and is stale for this frame slot.")
        source = download_comic_image(comic)
        suitability = analyze_xkcd_image(source)
        if not suitability.suitable:
            raise ValueError(f"Latest xkcd #{comic.number} is not suitable for Ditherloom: {', '.join(suitability.reasons)}")
    else:
        latest = fetch_xkcd_comic()
        comic, source, suitability = select_suitable_xkcd(
            latest.number,
            attempts=_positive_int(data.get("attempts")) or DEFAULT_RANDOM_ATTEMPTS,
            seed=_positive_int(data.get("seed")),
            exclude_numbers=excluded_numbers,
        )
        if not suitability.suitable:
            raise ValueError(f"No suitable xkcd comic found after the configured attempts: {', '.join(suitability.reasons)}")
    render = render_xkcd_card(comic, source, suitability)
    write_artifact(render.artifact, payload_dir, stem)
    return render.artifact, comic, suitability
STALE_FRONTEND_ENTITY_UNIQUE_ID_SUFFIXES = {
    "sync_wifi_wake_window",
    "synchronise_wifi_wake_window",
    "synchronize_wifi_wake_window",
    "sync_wake_window",
    "send_weather_to_frame",
    "frame_schedule_status",
}
STALE_FRONTEND_ENTITY_ID_SUFFIXES = {
    "sync_wifi_wake_window",
    "synchronise_wifi_wake_window",
    "synchronize_wifi_wake_window",
    "sync_wake_window",
    "send_weather_to_frame",
    "frame_schedule_status",
}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.http.register_view(DitherloomDiscoveryView(hass))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")
    coordinator = DitherloomRuntime(hass, entry, store)
    await coordinator.async_load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_start()
    _async_remove_stale_frontend_entities(hass, entry)

    hass.http.register_view(DitherloomPreviewView(coordinator))
    hass.http.register_view(DitherloomComicSampleView(coordinator))
    hass.http.register_view(DitherloomWeatherSampleView(coordinator))
    hass.http.register_view(DitherloomFrameAwakeView(coordinator))
    hass.http.register_view(DitherloomFrameSleepingView(coordinator))

    async def handle_render_weather(call: ServiceCall) -> None:
        await _handle_weather_service(coordinator, call, publish=False, send_to_frame=False, action="render weather")

    async def handle_send_weather(call: ServiceCall) -> None:
        await _handle_weather_service(coordinator, call, publish=True, send_to_frame=True, action="send weather")

    async def handle_render_sun(call: ServiceCall) -> None:
        await _handle_sun_service(coordinator, call, publish=False, send_to_frame=False, action="render sunrise / sunset")

    async def handle_send_sun(call: ServiceCall) -> None:
        await _handle_sun_service(coordinator, call, publish=True, send_to_frame=True, action="send sunrise / sunset")

    async def handle_render_moon(call: ServiceCall) -> None:
        await _handle_moon_service(coordinator, call, publish=False, send_to_frame=False, action="render moon phase")

    async def handle_send_moon(call: ServiceCall) -> None:
        await _handle_moon_service(coordinator, call, publish=True, send_to_frame=True, action="send moon phase")

    async def handle_render_xkcd(call: ServiceCall) -> None:
        await _handle_xkcd_service(coordinator, call, publish=False, send_to_frame=False, action="render xkcd")

    async def handle_send_xkcd(call: ServiceCall) -> None:
        await _handle_xkcd_service(coordinator, call, publish=True, send_to_frame=True, action="send xkcd")

    async def handle_render_astrology(call: ServiceCall) -> None:
        await _handle_astrology_service(coordinator, call, publish=False, send_to_frame=False, action="render astrology")

    async def handle_send_astrology(call: ServiceCall) -> None:
        await _handle_astrology_service(coordinator, call, publish=True, send_to_frame=True, action="send astrology")

    hass.services.async_register(DOMAIN, SERVICE_RENDER_WEATHER, handle_render_weather)
    hass.services.async_register(DOMAIN, SERVICE_SEND_WEATHER, handle_send_weather)
    hass.services.async_register(DOMAIN, SERVICE_RENDER_SUN, handle_render_sun)
    hass.services.async_register(DOMAIN, SERVICE_SEND_SUN, handle_send_sun)
    hass.services.async_register(DOMAIN, SERVICE_RENDER_MOON, handle_render_moon)
    hass.services.async_register(DOMAIN, SERVICE_SEND_MOON, handle_send_moon)
    hass.services.async_register(DOMAIN, SERVICE_RENDER_XKCD, handle_render_xkcd)
    hass.services.async_register(DOMAIN, SERVICE_SEND_XKCD, handle_send_xkcd)
    hass.services.async_register(DOMAIN, SERVICE_RENDER_ASTROLOGY, handle_render_astrology)
    hass.services.async_register(DOMAIN, SERVICE_SEND_ASTROLOGY, handle_send_astrology)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _async_remove_stale_frontend_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    registry = er.async_get(hass)
    expected_unique_ids = {
        f"{entry.entry_id}_{suffix}" for suffix in STALE_FRONTEND_ENTITY_UNIQUE_ID_SUFFIXES
    }
    for entity_entry in list(registry.entities.values()):
        if not _is_ditherloom_registry_entry(entity_entry, entry):
            continue
        if _is_stale_frontend_entity(entity_entry, expected_unique_ids):
            registry.async_remove(entity_entry.entity_id)


def _is_ditherloom_registry_entry(entity_entry: Any, entry: ConfigEntry) -> bool:
    if getattr(entity_entry, "config_entry_id", None) == entry.entry_id:
        return True
    if getattr(entity_entry, "platform", None) == DOMAIN:
        return True
    return "ditherloom" in str(getattr(entity_entry, "entity_id", "")).lower()


def _is_stale_frontend_entity(entity_entry: Any, expected_unique_ids: set[str]) -> bool:
    if getattr(entity_entry, "unique_id", None) in expected_unique_ids:
        return True
    entity_id = str(getattr(entity_entry, "entity_id", "")).lower()
    unique_id = str(getattr(entity_entry, "unique_id", "")).lower()
    if any(entity_id.endswith(f".{suffix}") or entity_id.endswith(f"_{suffix}") for suffix in STALE_FRONTEND_ENTITY_ID_SUFFIXES):
        return True
    if any(unique_id.endswith(suffix) for suffix in STALE_FRONTEND_ENTITY_UNIQUE_ID_SUFFIXES):
        return True
    return getattr(entity_entry, "original_name", None) in STALE_FRONTEND_ENTITY_NAMES or getattr(entity_entry, "name", None) in STALE_FRONTEND_ENTITY_NAMES


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator:
        coordinator.async_cancel_weather_refresh()
        coordinator.async_cancel_astrology_daily_refresh()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _handle_weather_service(
    coordinator: DitherloomRuntime,
    call: ServiceCall,
    publish: bool,
    send_to_frame: bool,
    action: str,
) -> None:
    await coordinator.async_run_weather_action(
        dict(call.data),
        publish=publish,
        send_to_frame=send_to_frame,
        action=action,
    )


async def _handle_sun_service(
    coordinator: DitherloomRuntime,
    call: ServiceCall,
    publish: bool,
    send_to_frame: bool,
    action: str,
) -> None:
    await coordinator.async_run_sun_action(
        dict(call.data),
        publish=publish,
        send_to_frame=send_to_frame,
        action=action,
    )


async def _handle_moon_service(
    coordinator: DitherloomRuntime,
    call: ServiceCall,
    publish: bool,
    send_to_frame: bool,
    action: str,
) -> None:
    await coordinator.async_run_moon_action(
        dict(call.data),
        publish=publish,
        send_to_frame=send_to_frame,
        action=action,
    )


async def _handle_xkcd_service(
    coordinator: "DitherloomRuntime",
    call: ServiceCall,
    publish: bool,
    send_to_frame: bool,
    action: str,
) -> None:
    await coordinator.async_run_xkcd_action(
        dict(call.data),
        publish=publish,
        send_to_frame=send_to_frame,
        action=action,
    )


async def _handle_astrology_service(
    coordinator: "DitherloomRuntime",
    call: ServiceCall,
    publish: bool,
    send_to_frame: bool,
    action: str,
) -> None:
    await coordinator.async_run_astrology_action(
        dict(call.data),
        publish=publish,
        send_to_frame=send_to_frame,
        action=action,
    )


@dataclass
class DitherloomRuntime:
    hass: HomeAssistant
    entry: ConfigEntry
    store: Store
    payload_dir: Path = field(init=False)
    last_status: str = "idle"
    last_metadata: dict[str, Any] = field(default_factory=dict)
    latest_payload_name: str = "weather-current"
    _weather_refresh_unsub: CALLBACK_TYPE | None = field(default=None, init=False, repr=False)
    _astrology_daily_refresh_unsub: CALLBACK_TYPE | None = field(default=None, init=False, repr=False)
    _weather_refresh_running: bool = field(default=False, init=False, repr=False)
    _listeners: list[Callable[[], None]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self.payload_dir = Path(self.hass.config.path("ditherloom_payloads", self.entry.entry_id))

    @property
    def options(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    async def async_load(self) -> None:
        self.payload_dir.mkdir(parents=True, exist_ok=True)
        stored = await self.store.async_load()
        if stored:
            self.last_status = stored.get("last_status", "idle")
            self.last_metadata = stored.get("last_metadata", {})

    async def async_start(self) -> None:
        self._schedule_weather_refresh()
        self._schedule_astrology_daily_refresh()
        self.hass.async_create_task(self._async_startup_refresh())

    async def _async_startup_refresh(self) -> None:
        try:
            await self.async_refresh_content_payload(reason="startup")
        except Exception as exc:
            _LOGGER.warning("Ditherloom startup content refresh failed: %s", exc)
            self.last_status = "startup_refresh_failed"
            self.last_metadata[ATTR_LAST_ERROR] = f"Startup content refresh failed: {type(exc).__name__}: {exc}"
            self.last_metadata["startup_refresh_last_failed_at"] = datetime.now(timezone.utc).isoformat()
            await self.async_save()

    async def async_save(self) -> None:
        await self.store.async_save(
            {
                "last_status": self.last_status,
                "last_metadata": self.last_metadata,
            }
        )
        self._notify_listeners()

    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        self._listeners.append(listener)

        def remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def async_run_weather_action(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        action: str,
    ) -> dict[str, Any]:
        try:
            return await self.async_render_weather(data, publish=publish, send_to_frame=send_to_frame)
        except Exception as exc:
            message = f"Ditherloom {action} failed: {type(exc).__name__}: {exc}"
            self.last_status = "error"
            self.last_metadata[ATTR_LAST_ERROR] = message
            await self.async_save()
            self._create_notification(f"Ditherloom {action} failed", message)
            raise HomeAssistantError(message) from exc

    async def async_run_sun_action(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        action: str,
    ) -> dict[str, Any]:
        try:
            return await self.async_render_sun(data, publish=publish, send_to_frame=send_to_frame)
        except Exception as exc:
            message = f"Ditherloom {action} failed: {type(exc).__name__}: {exc}"
            self.last_status = "error"
            self.last_metadata[ATTR_LAST_ERROR] = message
            await self.async_save()
            self._create_notification(f"Ditherloom {action} failed", message)
            raise HomeAssistantError(message) from exc

    async def async_run_moon_action(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        action: str,
    ) -> dict[str, Any]:
        try:
            return await self.async_render_moon(data, publish=publish, send_to_frame=send_to_frame)
        except Exception as exc:
            message = f"Ditherloom {action} failed: {type(exc).__name__}: {exc}"
            self.last_status = "error"
            self.last_metadata[ATTR_LAST_ERROR] = message
            await self.async_save()
            self._create_notification(f"Ditherloom {action} failed", message)
            raise HomeAssistantError(message) from exc

    async def async_run_xkcd_action(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        action: str,
    ) -> dict[str, Any]:
        try:
            return await self.async_render_xkcd(data, publish=publish, send_to_frame=send_to_frame)
        except Exception as exc:
            message = f"Ditherloom {action} failed: {type(exc).__name__}: {exc}"
            self.last_status = "error"
            self.last_metadata[ATTR_LAST_ERROR] = message
            await self.async_save()
            self._create_notification(f"Ditherloom {action} failed", message)
            raise HomeAssistantError(message) from exc

    async def async_run_astrology_action(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        action: str,
    ) -> dict[str, Any]:
        try:
            return await self.async_render_astrology(data, publish=publish, send_to_frame=send_to_frame)
        except Exception as exc:
            message = f"Ditherloom {action} failed: {type(exc).__name__}: {exc}"
            self.last_status = "error"
            self.last_metadata[ATTR_LAST_ERROR] = message
            await self.async_save()
            self._create_notification(f"Ditherloom {action} failed", message)
            raise HomeAssistantError(message) from exc

    async def async_send_cached_weather_action(self) -> dict[str, Any]:
        try:
            return await self.async_send_cached_weather()
        except Exception as exc:
            message = f"Ditherloom send weather failed: {type(exc).__name__}: {exc}"
            self.last_status = "error"
            self.last_metadata[ATTR_LAST_ERROR] = message
            await self.async_save()
            self._create_notification("Ditherloom send weather failed", message)
            raise HomeAssistantError(message) from exc

    async def async_send_cached_weather(self) -> dict[str, Any]:
        if not self.payload_path().exists() or ATTR_CRC32 not in self.last_metadata:
            await self.async_render_selected_content(reason="manual_missing_payload")
        packed = await self.hass.async_add_executor_job(self.payload_path().read_bytes)
        crc32 = str(self.last_metadata[ATTR_CRC32])
        await self.async_send_to_frame(packed, crc32)
        self.last_status = "sent"
        self.last_metadata["manual_send_last_success_at"] = datetime.now(timezone.utc).isoformat()
        self.last_metadata.pop(ATTR_LAST_ERROR, None)
        await self.async_save()
        return dict(self.last_metadata)

    async def async_handle_frame_awake(self, data: dict[str, Any], remote_addr: str | None = None) -> dict[str, Any]:
        await _store_frame_provided_ha_config(self.hass, self.entry, data)

        now = datetime.now(timezone.utc)
        host = str(data.get("ip") or data.get("host") or remote_addr or self.options.get(CONF_FRAME_HOST) or "").strip()
        port = _positive_int(data.get("port")) or int(self.options.get(CONF_FRAME_PORT, DEFAULT_FRAME_PORT))
        target_slot = self._selected_display_slot()
        if not host:
            raise ValueError("Frame awake callback did not include a usable host address")
        if target_slot < 1 or target_slot > DEVICE_SLOT_COUNT:
            raise ValueError(f"Frame target slot {target_slot} is outside the supported slot range")

        self.last_status = "frame_awake_received"
        self.last_metadata["frame_awake"] = {
            "received_at": now.isoformat(),
            "remote_addr": remote_addr or "",
            "host": host,
            "port": port,
            "target_slot": target_slot,
            "serial": data.get("serial"),
            "library_id": data.get("library_id") or data.get("libraryId"),
            "gateway_protocol": data.get("gateway_protocol") or data.get("gatewayProtocol"),
            "wake_reason": data.get("wake_reason") or data.get("wakeReason"),
            "wake_window_seconds": data.get("wake_window_seconds") or data.get("wakeWindowSeconds"),
            "max_jobs_per_wake": data.get("max_jobs_per_wake") or data.get("maxJobsPerWake"),
            "ha_config": _frame_provided_ha_config(self.options),
        }
        self.last_metadata["frame_awake_last_received_at"] = now.isoformat()
        self.last_metadata.pop("frame_awake_last_completion_command", None)
        self.last_metadata.pop("frame_awake_last_completion_sent_at", None)
        self.last_metadata.pop("frame_awake_last_completion_response", None)
        self.last_metadata.pop("frame_awake_last_completion_ok", None)
        self.last_metadata["frame_sleeping_expected_after_completion"] = False
        await self.async_save()

        jobs = await self._frame_sync_jobs()
        if not jobs:
            self.last_status = "frame_awake_no_jobs"
            self.last_metadata["frame_awake_last_no_jobs_at"] = now.isoformat()
            self.last_metadata["frame_awake_last_no_jobs_host"] = host
            self.last_metadata["frame_awake_last_no_jobs_port"] = port
            self.last_metadata["frame_awake_last_no_jobs_target_slot"] = target_slot
            self.last_metadata["frame_awake_last_no_jobs_providers"] = self._enabled_content_providers()
            self.last_metadata["frame_sleeping_expected_after_completion"] = False
            await self.async_save()
            return {
                "accepted": True,
                "mode": "gateway_push",
                "has_jobs": False,
                "job_count": 0,
                "message": "no frame sync jobs queued",
                "slot": target_slot,
                "display": False,
            }

        self.hass.async_create_task(self.async_deliver_cached_content_after_frame_callback(host, port, target_slot, jobs))
        self.last_metadata["frame_sleeping_expected_after_completion"] = True
        await self.async_save()
        return {
            "accepted": True,
            "mode": "gateway_push",
            "has_jobs": True,
            "job_count": len(jobs),
            "preview_url": self.last_metadata.get(ATTR_PREVIEW_URL),
            "crc32": self.last_metadata.get(ATTR_CRC32),
            "length": self.last_metadata.get("packed_length"),
            "slot": target_slot,
            "display": True,
        }

    async def async_deliver_cached_content_after_frame_callback(
        self,
        host: str,
        port: int,
        target_slot: int,
        jobs: list[dict[str, Any]],
    ) -> None:
        # Let the ESP32-C3 finish the outbound frame_awake HTTP response and
        # return to its single Gateway listener before HA opens the delivery
        # client. Without this handoff gap, the first Gateway PING can time out.
        await asyncio.sleep(1.5)
        await self.async_deliver_cached_content_to_announced_frame(host, port, target_slot, jobs)

    async def async_deliver_cached_content_to_announced_frame(
        self,
        host: str,
        port: int,
        target_slot: int,
        jobs: list[dict[str, Any]] | None = None,
    ) -> None:
        try:
            if jobs is None:
                jobs = await self._frame_sync_jobs()
            display_slot = self._selected_display_slot()
            ha_rotation = self._ha_rotation_config()
            gateway_status = await self.hass.async_add_executor_job(_send_gateway_batch_jobs, host, port, jobs, display_slot, ha_rotation)
            synced_at = datetime.now(timezone.utc).isoformat()
            completion = gateway_status.get("ha_completion") or {}
            if not completion or not completion.get("ok"):
                raise RuntimeError(f"Gateway delivery did not complete with HACOMPLETE all_jobs_complete: {completion or gateway_status}")
            for job in jobs:
                await self._mark_provider_frame_synced(str(job["provider_id"]), str(job["crc32"]), synced_at)
            delivered_jobs = [
                {
                    "synced_at": synced_at,
                    "provider_id": job.get("provider_id"),
                    "provider_name": job.get("provider_name"),
                    "slot": job.get("slot"),
                    "crc32": job.get("crc32"),
                    "content_id": job.get("content_id"),
                    "date_label": job.get("date_label"),
                    "source": job.get("content_source"),
                    "source_name": job.get("source_name"),
                    "source_url": job.get("source_url"),
                    "attribution": job.get("attribution"),
                    "attribution_url": job.get("attribution_url"),
                    "license": job.get("license"),
                    "license_url": job.get("license_url"),
                }
                for job in jobs
            ]
            self.last_status = "frame_awake_sent"
            self.last_metadata["frame_awake_last_success_at"] = synced_at
            self.last_metadata["frame_awake_last_send_host"] = host
            self.last_metadata["frame_awake_last_send_port"] = port
            self.last_metadata["frame_awake_last_target_slot"] = display_slot
            self.last_metadata["frame_awake_last_synced_providers"] = [job["provider_id"] for job in jobs]
            self.last_metadata["frame_content_last_delivered_at"] = synced_at
            self.last_metadata["frame_content_last_delivered_count"] = len(delivered_jobs)
            self.last_metadata["frame_content_last_delivered_slots"] = [job["slot"] for job in delivered_jobs]
            self.last_metadata["frame_content_last_delivered_crc32"] = [job["crc32"] for job in delivered_jobs]
            self.last_metadata["frame_content_last_delivered_content_ids"] = [job["content_id"] for job in delivered_jobs]
            self.last_metadata["frame_content_last_delivered_attributions"] = [job.get("attribution") for job in delivered_jobs]
            self.last_metadata["frame_content_last_delivered_licenses"] = [job.get("license") for job in delivered_jobs]
            self.last_metadata["frame_awake_last_delivered_jobs"] = delivered_jobs
            self.last_metadata["frame_awake_last_completion_command"] = completion.get("command")
            self.last_metadata["frame_awake_last_completion_sent_at"] = completion.get("sent_at")
            self.last_metadata["frame_awake_last_completion_response"] = completion.get("response")
            self.last_metadata["frame_awake_last_completion_ok"] = bool(completion.get("ok"))
            self.last_metadata["frame_sleeping_expected_after_completion"] = True
            if gateway_status.get("ha_rotation"):
                self.last_metadata["ha_rotation"] = gateway_status["ha_rotation"]
            self._record_delivered_comic_exclusions(delivered_jobs)
            self.hass.async_create_task(self._refresh_delivered_comic_successors(delivered_jobs, synced_at))
            self.last_metadata.pop(ATTR_LAST_ERROR, None)
        except Exception as exc:
            self.last_status = "frame_awake_send_failed"
            self.last_metadata[ATTR_LAST_ERROR] = f"Frame awake delivery failed: {type(exc).__name__}: {exc}"
            self.last_metadata["frame_awake_last_failed_at"] = datetime.now(timezone.utc).isoformat()
            self.last_metadata["frame_awake_last_completion_ok"] = False
            self._create_notification("Ditherloom frame awake delivery failed", str(self.last_metadata[ATTR_LAST_ERROR]))
        finally:
            await self.async_save()

    async def async_deliver_cached_weather_to_announced_frame(self, host: str, port: int, target_slot: int) -> None:
        await self.async_deliver_cached_content_to_announced_frame(host, port, target_slot)

    async def async_handle_frame_sleeping(self, data: dict[str, Any], remote_addr: str | None = None) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        self.last_status = "frame_sleeping"
        self.last_metadata["frame_sleeping"] = {
            "received_at": now.isoformat(),
            "remote_addr": remote_addr or "",
            "serial": data.get("serial"),
            "library_id": data.get("library_id") or data.get("libraryId"),
            "sleep_reason": data.get("sleep_reason") or data.get("sleepReason"),
            "completed_jobs": data.get("completed_jobs") or data.get("completedJobs"),
            "displayed_slot": data.get("displayed_slot") or data.get("displayedSlot"),
            "next_wake_seconds": data.get("next_wake_seconds") or data.get("nextWakeSeconds"),
        }
        next_wake_seconds = _positive_int(data.get("next_wake_seconds") or data.get("nextWakeSeconds"))
        if next_wake_seconds is not None:
            self.last_metadata["frame_next_wake_at"] = (now + timedelta(seconds=next_wake_seconds)).isoformat()
        self.last_metadata["frame_sleeping_last_received_at"] = now.isoformat()
        self.last_metadata["frame_sleeping_expected_after_completion"] = False
        await self.async_save()
        return {"accepted": True, "message": "sleep recorded"}

    async def async_refresh_weather_payload(self, reason: str = "timer") -> dict[str, Any]:
        return await self.async_refresh_content_payload(reason)

    async def async_refresh_content_payload(self, reason: str = "timer") -> dict[str, Any]:
        refreshed: list[str] = []
        failed: dict[str, str] = {}
        force_prerender = reason in {"startup", "timer"}
        for provider in self._enabled_content_providers():
            metadata = await self._read_cached_metadata(provider)
            if force_prerender or metadata is None or not self._cached_content_is_fresh(provider, metadata):
                try:
                    await self.async_render_provider_to_cache(provider)
                except Exception as exc:
                    failed[provider] = f"{type(exc).__name__}: {exc}"
                    continue
                refreshed.append(provider)
        selected = self._selected_content_provider()
        metadata = await self.async_activate_cached_content(selected, reason=reason)
        if metadata is None and selected not in failed:
            try:
                metadata = await self.async_render_provider_to_cache(selected)
                await self.async_activate_cached_content(selected, reason=reason)
            except Exception as exc:
                failed[selected] = f"{type(exc).__name__}: {exc}"
        if metadata is None:
            for provider in self._enabled_content_providers():
                metadata = await self.async_activate_cached_content(provider, reason=reason)
                if metadata is not None:
                    break
        if metadata is None and failed:
            message = "Content refresh failed for: " + "; ".join(f"{provider}: {error}" for provider, error in failed.items())
            self.last_status = "content_refresh_failed"
            self.last_metadata[ATTR_LAST_ERROR] = message
            self.last_metadata["content_refresh_failed_providers"] = failed
            self.last_metadata["content_refresh_last_failed_at"] = datetime.now(timezone.utc).isoformat()
            await self.async_save()
            raise HomeAssistantError(message)
        provider_id = str((metadata or {}).get("provider_id") or selected)
        self.last_status = "content_refresh_partial" if failed else f"{provider_id}_ready"
        self.last_metadata["content_refresh_reason"] = reason
        self.last_metadata["content_refreshed_providers"] = refreshed
        self.last_metadata["content_refresh_failed_providers"] = failed
        self.last_metadata["content_refresh_last_success_at"] = datetime.now(timezone.utc).isoformat()
        self.last_metadata["content_refresh_interval_minutes"] = self._effective_update_interval_minutes()
        self.last_metadata["weather_refresh_reason"] = reason
        self.last_metadata["weather_refresh_last_success_at"] = self.last_metadata["content_refresh_last_success_at"]
        self.last_metadata["weather_refresh_interval_minutes"] = self.last_metadata["content_refresh_interval_minutes"]
        if failed:
            self.last_metadata[ATTR_LAST_ERROR] = (
                "Content refresh partially failed for: "
                + "; ".join(f"{provider}: {error}" for provider, error in failed.items())
            )
            self.last_metadata["content_refresh_last_failed_at"] = datetime.now(timezone.utc).isoformat()
            self._create_notification("Ditherloom content refresh failed", str(self.last_metadata[ATTR_LAST_ERROR]))
        else:
            self.last_metadata.pop(ATTR_LAST_ERROR, None)
            self.last_metadata.pop("content_refresh_last_failed_at", None)
        self._schedule_weather_refresh()
        await self.async_save()
        return metadata or {}

    async def async_render_provider_to_cache(self, provider: str) -> dict[str, Any]:
        render_data = self._comic_render_exclusion_data(provider)
        if provider == "sunrise_sunset":
            metadata = await self.async_render_sun({}, publish=False, send_to_frame=False, cache_provider_id=provider)
        elif provider == "moon_phase":
            metadata = await self.async_render_moon({}, publish=False, send_to_frame=False, cache_provider_id=provider)
        elif provider == "xkcd_comic":
            metadata = await self.async_render_xkcd(render_data, publish=False, send_to_frame=False, cache_provider_id=provider)
        elif provider in {
            PROVIDER_DIESEL_SWEETIES,
            PROVIDER_MIMI_EUNICE,
        }:
            metadata = await self.async_render_webcomic(render_data, publish=False, send_to_frame=False, cache_provider_id=provider)
        elif provider == PROVIDER_ASTROLOGY:
            metadata = await self.async_render_astrology({}, publish=False, send_to_frame=False, cache_provider_id=provider)
        elif provider in ASTRONOMY_PROVIDER_IDS:
            metadata = await self.async_render_astronomy({}, publish=False, send_to_frame=False, cache_provider_id=provider)
        elif provider in WEATHER_PROVIDER_IDS:
            metadata = await self.async_render_weather({}, publish=False, send_to_frame=False, cache_provider_id=provider)
        else:
            metadata = await self.async_render_weather({}, publish=False, send_to_frame=False, cache_provider_id=PROVIDER_WEATHER)
        metadata["selected_provider_id"] = provider
        metadata["display_rotation_enabled"] = self._display_rotation_enabled()
        metadata["display_rotation_interval_minutes"] = self._display_rotation_interval_minutes()
        metadata["selected_provider_cache"] = "rendered"
        await self._write_cached_metadata(provider, metadata)
        return metadata

    async def async_render_selected_content(self, reason: str = "timer") -> dict[str, Any]:
        provider = self._selected_content_provider()
        cached = await self.async_activate_cached_content(provider, reason=reason)
        if cached is not None:
            return cached
        if provider == "sunrise_sunset":
            metadata = await self.async_render_sun({}, publish=True, send_to_frame=False, cache_provider_id=provider)
        elif provider == "moon_phase":
            metadata = await self.async_render_moon({}, publish=True, send_to_frame=False, cache_provider_id=provider)
        elif provider == "xkcd_comic":
            metadata = await self.async_render_xkcd({}, publish=True, send_to_frame=False, cache_provider_id=provider)
        elif provider in {
            PROVIDER_DIESEL_SWEETIES,
            PROVIDER_MIMI_EUNICE,
        }:
            metadata = await self.async_render_webcomic({}, publish=True, send_to_frame=False, cache_provider_id=provider)
        elif provider == PROVIDER_ASTROLOGY:
            metadata = await self.async_render_astrology({}, publish=True, send_to_frame=False, cache_provider_id=provider)
        elif provider in ASTRONOMY_PROVIDER_IDS:
            metadata = await self.async_render_astronomy({}, publish=True, send_to_frame=False, cache_provider_id=provider)
        elif provider in WEATHER_PROVIDER_IDS:
            metadata = await self.async_render_weather({}, publish=True, send_to_frame=False, cache_provider_id=provider)
        else:
            metadata = await self.async_render_weather({}, publish=True, send_to_frame=False, cache_provider_id=PROVIDER_WEATHER)
        metadata["selected_provider_id"] = provider
        metadata["display_rotation_enabled"] = self._display_rotation_enabled()
        metadata["display_rotation_interval_minutes"] = self._display_rotation_interval_minutes()
        metadata["selected_provider_reason"] = reason
        metadata["selected_provider_cache"] = "rendered"
        self.last_metadata.update(
            {
                "selected_provider_id": provider,
                "display_rotation_enabled": metadata["display_rotation_enabled"],
                "display_rotation_interval_minutes": metadata["display_rotation_interval_minutes"],
                "selected_provider_reason": reason,
                "selected_provider_cache": "rendered",
            }
        )
        await self._write_cached_metadata(provider, metadata)
        await self.async_save()
        return metadata

    async def async_render_webcomic(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        cache_provider_id: str | None = None,
    ) -> dict[str, Any]:
        from .webcomic_provider import render_webcomic_provider

        if cache_provider_id is None:
            provider = str(data.get("provider_id") or "")
            if provider not in {
                PROVIDER_DIESEL_SWEETIES,
                PROVIDER_MIMI_EUNICE,
            }:
                raise HomeAssistantError("Choose a supported Comics provider.")
        else:
            provider = cache_provider_id
        opts = self.options
        stem = self._provider_payload_name(cache_provider_id) if cache_provider_id else self.latest_payload_name
        excluded_urls = {str(url) for url in data.get("exclude_source_urls", []) if str(url).strip()}
        artifact, source, selection = await self.hass.async_add_executor_job(
            partial(
                render_webcomic_provider,
                provider,
                self.payload_dir,
                stem,
                excluded_source_urls=excluded_urls,
            )
        )
        if cache_provider_id:
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.ppbin", self.payload_path())
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.preview.png", self.preview_path())

        metadata = dict(artifact.metadata)
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["provider_id"] = source.provider_id
        metadata["provider_name"] = source.provider_name
        metadata["card_renderer_version"] = CARD_RENDERER_VERSION
        metadata["source"] = source.source_id
        metadata["source_name"] = source.provider_name
        metadata["source_url"] = selection.candidate.source_url
        metadata["image_url"] = selection.candidate.image_url
        metadata["attribution"] = source.attribution
        metadata["attribution_url"] = source.attribution_url
        metadata["license"] = source.license_name
        metadata["license_url"] = source.license_url
        metadata["comic_title"] = selection.candidate.title
        metadata["update_interval_minutes"] = self._effective_update_interval_minutes()
        metadata["wake_window_seconds"] = self._effective_wake_window_seconds()
        metadata["wake_window_minutes"] = self._effective_wake_window_minutes()
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)
        metadata["content_rendered_at"] = metadata["rendered_at"]
        metadata["content_rendered_provider_id"] = metadata["provider_id"]
        metadata["content_rendered_provider_name"] = metadata["provider_name"]
        metadata["content_rendered_source_name"] = metadata["source_name"]
        metadata["content_rendered_attribution"] = metadata["attribution"]
        metadata["content_rendered_license"] = metadata["license"]
        metadata["content_rendered_content_id"] = metadata.get(ATTR_CONTENT_ID)
        metadata["content_rendered_crc32"] = metadata.get(ATTR_CRC32)
        for preserved_key in PRESERVED_RUNTIME_METADATA_KEYS:
            if preserved_key in self.last_metadata:
                metadata[preserved_key] = self.last_metadata[preserved_key]

        self.last_status = "rendered"
        self.last_metadata = metadata
        if publish:
            self.last_status = "rendered"
        if send_to_frame:
            await self.async_send_to_frame(artifact.packed, artifact.crc32)
            self.last_status = "sent"
            self.last_metadata.pop(ATTR_LAST_ERROR, None)
        await self.async_save()
        return metadata

    async def async_activate_cached_content(self, provider: str, reason: str) -> dict[str, Any] | None:
        metadata = await self._read_cached_metadata(provider)
        if metadata is None or not self._cached_content_is_fresh(provider, metadata):
            return None
        stem = self._provider_payload_name(provider)
        source_payload = self.payload_dir / f"{stem}.ppbin"
        source_preview = self.payload_dir / f"{stem}.preview.png"
        if not source_payload.exists() or not source_preview.exists():
            return None
        await self.hass.async_add_executor_job(shutil.copyfile, source_payload, self.payload_path())
        await self.hass.async_add_executor_job(shutil.copyfile, source_preview, self.preview_path())
        metadata = dict(metadata)
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["selected_provider_id"] = provider
        metadata["display_rotation_enabled"] = self._display_rotation_enabled()
        metadata["display_rotation_interval_minutes"] = self._display_rotation_interval_minutes()
        metadata["selected_provider_reason"] = reason
        metadata["selected_provider_cache"] = "cached"
        metadata["activated_at"] = datetime.now(timezone.utc).isoformat()
        for preserved_key in PRESERVED_RUNTIME_METADATA_KEYS:
            if preserved_key in self.last_metadata:
                metadata[preserved_key] = self.last_metadata[preserved_key]
        self.last_status = "rendered"
        self.last_metadata = metadata
        await self.async_save()
        return metadata

    async def async_render_astrology(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        cache_provider_id: str | None = None,
    ) -> dict[str, Any]:
        from .astrology_provider import ASTROLOGY_PROVIDER_ID, normalize_signs, render_astrology_provider

        if cache_provider_id is not None and cache_provider_id != ASTROLOGY_PROVIDER_ID:
            raise HomeAssistantError("Choose the supported Astrology provider.")
        opts = self.options
        stem = self._provider_payload_name(cache_provider_id) if cache_provider_id else self.latest_payload_name
        signs = normalize_signs(data.get(CONF_ASTROLOGY_SIGNS) or opts.get(CONF_ASTROLOGY_SIGNS))
        interval_minutes = self._effective_update_interval_minutes()
        render_now = datetime.now(self._local_timezone())
        artifact, card = await self.hass.async_add_executor_job(
            partial(
                render_astrology_provider,
                self.payload_dir,
                stem,
                signs=signs,
                interval_minutes=interval_minutes,
                now=render_now,
            )
        )
        if cache_provider_id:
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.ppbin", self.payload_path())
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.preview.png", self.preview_path())

        metadata = dict(artifact.metadata)
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["provider_id"] = ASTROLOGY_PROVIDER_ID
        metadata["provider_name"] = "Daily Astrology"
        metadata["card_renderer_version"] = CARD_RENDERER_VERSION
        metadata["astrology_enabled_signs"] = signs
        metadata["astrology_sign"] = card.sign
        metadata["astrology_sign_name"] = card.sign_name
        metadata["astrology_date_label"] = card.date_label
        metadata["astrology_moon_phase"] = card.moon_phase
        metadata["astrology_skyfield_status"] = card.skyfield_status
        metadata["astrology_headline"] = card.headline
        metadata["astrology_body"] = card.body
        metadata["update_interval_minutes"] = interval_minutes
        metadata["wake_window_seconds"] = self._effective_wake_window_seconds()
        metadata["wake_window_minutes"] = self._effective_wake_window_minutes()
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)
        metadata["content_rendered_at"] = metadata["rendered_at"]
        metadata["content_rendered_provider_id"] = metadata["provider_id"]
        metadata["content_rendered_provider_name"] = metadata["provider_name"]
        metadata["content_rendered_source_name"] = metadata["source_name"]
        metadata["content_rendered_attribution"] = metadata["attribution"]
        metadata["content_rendered_license"] = metadata["license"]
        metadata["content_rendered_content_id"] = metadata.get(ATTR_CONTENT_ID)
        metadata["content_rendered_crc32"] = metadata.get(ATTR_CRC32)
        for preserved_key in PRESERVED_RUNTIME_METADATA_KEYS:
            if preserved_key in self.last_metadata:
                metadata[preserved_key] = self.last_metadata[preserved_key]

        self.last_status = "rendered"
        self.last_metadata = metadata
        if publish:
            self.last_status = "rendered"
        if send_to_frame:
            await self.async_send_to_frame(artifact.packed, artifact.crc32)
            self.last_status = "sent"
            self.last_metadata.pop(ATTR_LAST_ERROR, None)
        await self.async_save()
        return metadata

    async def async_render_astronomy(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        cache_provider_id: str | None = None,
    ) -> dict[str, Any]:
        from .astronomy_provider import ASTRONOMY_PROVIDER_IDS as SOURCE_ASTRONOMY_PROVIDER_IDS
        from .astronomy_provider import ASTRONOMY_PROVIDER_NAMES, render_astronomy_provider

        provider = cache_provider_id or str(data.get("provider_id") or PROVIDER_ASTRONOMY_TONIGHT_SKY)
        if provider not in SOURCE_ASTRONOMY_PROVIDER_IDS:
            raise HomeAssistantError("Choose a supported Astronomy provider.")
        opts = self.options
        stem = self._provider_payload_name(cache_provider_id) if cache_provider_id else self.latest_payload_name
        latitude = _float_or_zero(data.get(CONF_LATITUDE) or opts.get(CONF_LATITUDE) or self.hass.config.latitude)
        longitude = _float_or_zero(data.get(CONF_LONGITUDE) or opts.get(CONF_LONGITUDE) or self.hass.config.longitude)
        location_name = str(data.get(CONF_LOCATION_NAME) or opts.get(CONF_LOCATION_NAME) or "Home")
        artifact, card = await self.hass.async_add_executor_job(
            partial(
                render_astronomy_provider,
                provider,
                self.payload_dir,
                stem,
                latitude=latitude,
                longitude=longitude,
                location_name=location_name,
                now=datetime.now(self._local_timezone()),
            )
        )
        if cache_provider_id:
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.ppbin", self.payload_path())
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.preview.png", self.preview_path())

        metadata = dict(artifact.metadata)
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["provider_id"] = provider
        metadata["provider_name"] = ASTRONOMY_PROVIDER_NAMES[provider]
        metadata["card_renderer_version"] = CARD_RENDERER_VERSION
        metadata["astronomy_card_provider"] = provider
        metadata["astronomy_date_label"] = card.date_label
        metadata["astronomy_skyfield_status"] = card.skyfield_status
        metadata["astronomy_headline"] = card.headline
        metadata["astronomy_lines"] = list(card.lines)
        metadata["update_interval_minutes"] = self._effective_update_interval_minutes()
        metadata["wake_window_seconds"] = self._effective_wake_window_seconds()
        metadata["wake_window_minutes"] = self._effective_wake_window_minutes()
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)
        metadata["content_rendered_at"] = metadata["rendered_at"]
        metadata["content_rendered_provider_id"] = metadata["provider_id"]
        metadata["content_rendered_provider_name"] = metadata["provider_name"]
        metadata["content_rendered_source_name"] = metadata["source_name"]
        metadata["content_rendered_attribution"] = metadata["attribution"]
        metadata["content_rendered_license"] = metadata["license"]
        metadata["content_rendered_content_id"] = metadata.get(ATTR_CONTENT_ID)
        metadata["content_rendered_crc32"] = metadata.get(ATTR_CRC32)
        for preserved_key in PRESERVED_RUNTIME_METADATA_KEYS:
            if preserved_key in self.last_metadata:
                metadata[preserved_key] = self.last_metadata[preserved_key]

        self.last_status = "rendered"
        self.last_metadata = metadata
        if publish:
            self.last_status = "rendered"
        if send_to_frame:
            await self.async_send_to_frame(artifact.packed, artifact.crc32)
            self.last_status = "sent"
            self.last_metadata.pop(ATTR_LAST_ERROR, None)
        await self.async_save()
        return metadata

    async def async_render_weather(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        cache_provider_id: str | None = None,
    ) -> dict[str, Any]:
        from .open_meteo import (
            NOMINATIM_ATTRIBUTION,
            NOMINATIM_ATTRIBUTION_URL,
            NOMINATIM_LICENSE,
            NOMINATIM_LICENSE_URL,
            OPEN_METEO_ATTRIBUTION,
            OPEN_METEO_ATTRIBUTION_URL,
            OPEN_METEO_CHANGES,
            OPEN_METEO_LICENSE,
            OPEN_METEO_LICENSE_URL,
            fetch_open_meteo_card,
            fetch_open_meteo_forecast,
            fetch_open_meteo_hourly,
        )
        from .renderer import WeatherRadarData

        opts = self.options
        picked_location = data.get(CONF_WEATHER_LOCATION)
        if isinstance(picked_location, dict):
            latitude = str(picked_location.get(CONF_LATITUDE) or opts.get(CONF_LATITUDE) or "0")
            longitude = str(picked_location.get(CONF_LONGITUDE) or opts.get(CONF_LONGITUDE) or "0")
            location = str(data.get(CONF_LOCATION_NAME) or data.get("location") or "")
        else:
            latitude = str(data.get(CONF_LATITUDE) or opts.get(CONF_LATITUDE) or "0")
            longitude = str(data.get(CONF_LONGITUDE) or opts.get(CONF_LONGITUDE) or "0")
            location = str(data.get(CONF_LOCATION_NAME) or data.get("location") or opts.get(CONF_LOCATION_NAME) or "Home")

        temperature_unit = str(data.get(CONF_TEMPERATURE_UNIT) or opts.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT))
        wind_speed_unit = str(data.get(CONF_WIND_SPEED_UNIT) or opts.get(CONF_WIND_SPEED_UNIT, DEFAULT_WIND_SPEED_UNIT))
        provider_id = cache_provider_id or PROVIDER_WEATHER
        radar_api_key = str(
            data.get(CONF_WEATHER_RADAR_OPENWEATHER_API_KEY)
            or opts.get(CONF_WEATHER_RADAR_OPENWEATHER_API_KEY)
            or ""
        ).strip()
        radar_layer = str(
            data.get(CONF_WEATHER_RADAR_OPENWEATHER_LAYER)
            or opts.get(CONF_WEATHER_RADAR_OPENWEATHER_LAYER)
            or "precipitation_new"
        ).strip()
        radar_zoom = int(
            data.get(CONF_WEATHER_RADAR_OPENWEATHER_ZOOM)
            or opts.get(CONF_WEATHER_RADAR_OPENWEATHER_ZOOM)
            or 6
        )
        radar_palette = str(
            data.get(CONF_WEATHER_RADAR_PALETTE)
            or opts.get(CONF_WEATHER_RADAR_PALETTE)
            or DEFAULT_WEATHER_RADAR_PALETTE
        ).strip()
        radar_attribution = str(
            data.get(CONF_WEATHER_RADAR_ATTRIBUTION)
            or opts.get(CONF_WEATHER_RADAR_ATTRIBUTION)
            or "OpenWeather"
        ).strip()
        if provider_id in {PROVIDER_WEATHER_TODAY_TOMORROW, PROVIDER_WEATHER_7_DAY}:
            card_data = await self.hass.async_add_executor_job(
                fetch_open_meteo_forecast,
                latitude,
                longitude,
                location,
                temperature_unit,
                wind_speed_unit,
                7,
            )
        elif provider_id in {PROVIDER_WEATHER_PRECIPITATION, PROVIDER_WEATHER_UV, PROVIDER_WEATHER_WIND}:
            card_data = await self.hass.async_add_executor_job(
                fetch_open_meteo_hourly,
                latitude,
                longitude,
                location,
                wind_speed_unit,
            )
        elif provider_id == PROVIDER_WEATHER_RADAR:
            radar_payload = (
                await self.hass.async_add_executor_job(
                    _fetch_openweather_radar_snapshot,
                    latitude,
                    longitude,
                    radar_api_key,
                    radar_layer,
                    radar_zoom,
                    self.payload_dir / "radar_basemap_cache",
                )
                if radar_api_key
                else b""
            )
            card_data = WeatherRadarData(
                location=location or str(opts.get(CONF_LOCATION_NAME) or "Weather"),
                radar_image=radar_payload,
                updated=datetime.now().strftime("%H:%M"),
                source_entity_id="weather.radar_url",
                attribution=radar_attribution,
                palette=radar_palette,
            )
        else:
            card_data = await self.hass.async_add_executor_job(
                fetch_open_meteo_card,
                latitude,
                longitude,
                location,
                temperature_unit,
                wind_speed_unit,
            )
        display_mode = str(data.get(CONF_DISPLAY_MODE) or opts.get(CONF_DISPLAY_MODE, DEFAULT_DISPLAY_MODE))
        stem = self._provider_payload_name(cache_provider_id) if cache_provider_id else self.latest_payload_name
        artifact = await self.hass.async_add_executor_job(
            _render_weather_artifact_to_disk,
            card_data,
            display_mode,
            self.payload_dir,
            stem,
            provider_id,
        )
        if cache_provider_id:
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.ppbin", self.payload_path())
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.preview.png", self.preview_path())

        metadata = dict(artifact.metadata)
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["update_interval_minutes"] = self._effective_update_interval_minutes()
        metadata["wake_window_seconds"] = self._effective_wake_window_seconds()
        metadata["wake_window_minutes"] = self._effective_wake_window_minutes()
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)
        metadata["display_mode"] = display_mode
        metadata["temperature_unit"] = temperature_unit
        metadata["wind_speed_unit"] = wind_speed_unit
        metadata["provider_id"] = provider_id
        metadata["provider_name"] = _weather_provider_name(provider_id)
        metadata["weather_card_variant"] = provider_id
        metadata["card_renderer_version"] = CARD_RENDERER_VERSION
        if provider_id == PROVIDER_WEATHER_RADAR:
            metadata["source"] = "openweather_weather_maps"
            metadata["source_name"] = "OpenWeather Weather Maps"
            metadata["source_url"] = "https://openweathermap.org/api/weathermaps"
            metadata["attribution"] = card_data.attribution or "OpenWeather"
            metadata["attribution_url"] = "https://openweathermap.org/"
            metadata["license"] = "OpenWeather API terms"
            metadata["license_url"] = "https://openweathermap.org/terms"
            metadata["secondary_attribution"] = "OpenStreetMap contributors"
            metadata["secondary_attribution_url"] = "https://www.openstreetmap.org/copyright"
            metadata["secondary_license"] = "OpenStreetMap tile policy and ODbL/OSM contributor terms"
            metadata["secondary_license_url"] = "https://operations.osmfoundation.org/policies/tiles/"
            metadata["data_transformations"] = (
                "OpenWeather weather overlay tiles are assembled around the configured latitude/longitude and cropped "
                "to the radar panel. A cached OpenStreetMap basemap is used underneath for local map context. The selected "
                "Ditherloom-friendly radar palette is applied only to semi-transparent weather-overlay pixels, not to the "
                "basemap, before the 400x300 hybrid render; text rendered panel-safe."
            )
            metadata["openweather_layer"] = radar_layer
            metadata["openweather_zoom"] = radar_zoom
            metadata["openweather_palette"] = radar_palette
        else:
            metadata["source"] = "open_meteo"
            metadata["source_name"] = "Open-Meteo"
            metadata["source_url"] = OPEN_METEO_ATTRIBUTION_URL
            metadata["attribution"] = card_data.attribution or OPEN_METEO_ATTRIBUTION
            metadata["attribution_url"] = OPEN_METEO_ATTRIBUTION_URL
            metadata["license"] = OPEN_METEO_LICENSE
            metadata["license_url"] = OPEN_METEO_LICENSE_URL
            metadata["data_transformations"] = OPEN_METEO_CHANGES
        if provider_id != PROVIDER_WEATHER_RADAR and NOMINATIM_ATTRIBUTION in metadata["attribution"]:
            metadata["secondary_attribution"] = NOMINATIM_ATTRIBUTION
            metadata["secondary_attribution_url"] = NOMINATIM_ATTRIBUTION_URL
            metadata["secondary_license"] = NOMINATIM_LICENSE
            metadata["secondary_license_url"] = NOMINATIM_LICENSE_URL
        metadata["content_rendered_at"] = metadata["rendered_at"]
        metadata["content_rendered_provider_id"] = metadata["provider_id"]
        metadata["content_rendered_provider_name"] = metadata["provider_name"]
        metadata["content_rendered_source_name"] = metadata["source_name"]
        metadata["content_rendered_attribution"] = metadata["attribution"]
        metadata["content_rendered_license"] = metadata["license"]
        metadata["content_rendered_content_id"] = metadata.get(ATTR_CONTENT_ID)
        metadata["content_rendered_crc32"] = metadata.get(ATTR_CRC32)
        for preserved_key in PRESERVED_RUNTIME_METADATA_KEYS:
            if preserved_key in self.last_metadata:
                metadata[preserved_key] = self.last_metadata[preserved_key]

        self.last_status = "rendered"
        self.last_metadata = metadata

        if publish:
            self.last_status = "rendered"
        if send_to_frame:
            await self.async_send_to_frame(artifact.packed, artifact.crc32)
            self.last_status = "sent"
            self.last_metadata.pop(ATTR_LAST_ERROR, None)

        await self.async_save()
        return metadata

    async def async_render_sun(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        cache_provider_id: str | None = None,
    ) -> dict[str, Any]:
        from .sun_provider import build_sun_provider_data

        opts = self.options
        picked_location = data.get(CONF_WEATHER_LOCATION)
        if isinstance(picked_location, dict):
            latitude = str(picked_location.get(CONF_LATITUDE) or opts.get(CONF_LATITUDE) or "0")
            longitude = str(picked_location.get(CONF_LONGITUDE) or opts.get(CONF_LONGITUDE) or "0")
            location = str(data.get(CONF_LOCATION_NAME) or data.get("location") or opts.get(CONF_LOCATION_NAME) or "Home")
        else:
            latitude = str(data.get(CONF_LATITUDE) or opts.get(CONF_LATITUDE) or "0")
            longitude = str(data.get(CONF_LONGITUDE) or opts.get(CONF_LONGITUDE) or "0")
            location = str(data.get(CONF_LOCATION_NAME) or data.get("location") or opts.get(CONF_LOCATION_NAME) or "Home")

        render_target = self._time_sensitive_render_target(data)
        provider_data = build_sun_provider_data(
            latitude,
            longitude,
            location,
            self.hass.config.time_zone,
            current_datetime=render_target,
        )
        stem = self._provider_payload_name(cache_provider_id) if cache_provider_id else self.latest_payload_name
        artifact, card_data = await self.hass.async_add_executor_job(
            _render_sun_artifact_to_disk,
            provider_data,
            self.payload_dir,
            stem,
        )
        if cache_provider_id:
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.ppbin", self.payload_path())
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.preview.png", self.preview_path())

        metadata = dict(artifact.metadata)
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["render_target_at"] = render_target.isoformat()
        metadata["provider_id"] = "sunrise_sunset"
        metadata["provider_name"] = "Sunrise / Sunset"
        metadata["card_renderer_version"] = CARD_RENDERER_VERSION
        metadata["source"] = "local_solar_calculation"
        metadata["source_name"] = "Ditherloom local solar calculation"
        metadata["source_url"] = ""
        metadata["attribution"] = card_data.attribution
        metadata["attribution_url"] = ""
        metadata["license"] = ""
        metadata["license_url"] = ""
        metadata["data_transformations"] = (
            "Sunrise, sunset, twilight, day length, and golden-hour fields are calculated "
            "from configured coordinates and rendered into a Ditherloom e-ink card."
        )
        metadata["location"] = card_data.location
        metadata["date_label"] = card_data.date_label
        metadata["sunrise"] = card_data.sunrise
        metadata["sunset"] = card_data.sunset
        metadata["civil_dawn"] = card_data.civil_dawn
        metadata["civil_dusk"] = card_data.civil_dusk
        metadata["day_length"] = card_data.day_length
        metadata["golden_morning"] = card_data.golden_morning
        metadata["golden_evening"] = card_data.golden_evening
        metadata["primary_label"] = card_data.primary_label
        metadata["primary_value"] = card_data.primary_value
        metadata["secondary_prefix"] = card_data.secondary_prefix
        metadata["secondary_value"] = card_data.secondary_value
        metadata["update_interval_minutes"] = self._effective_update_interval_minutes()
        metadata["wake_window_seconds"] = self._effective_wake_window_seconds()
        metadata["wake_window_minutes"] = self._effective_wake_window_minutes()
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)
        metadata["content_rendered_at"] = metadata["rendered_at"]
        metadata["content_rendered_provider_id"] = metadata["provider_id"]
        metadata["content_rendered_provider_name"] = metadata["provider_name"]
        metadata["content_rendered_source_name"] = metadata["source_name"]
        metadata["content_rendered_attribution"] = metadata["attribution"]
        metadata["content_rendered_license"] = metadata["license"]
        metadata["content_rendered_content_id"] = metadata.get(ATTR_CONTENT_ID)
        metadata["content_rendered_crc32"] = metadata.get(ATTR_CRC32)
        for preserved_key in PRESERVED_RUNTIME_METADATA_KEYS:
            if preserved_key in self.last_metadata:
                metadata[preserved_key] = self.last_metadata[preserved_key]

        self.last_status = "rendered"
        self.last_metadata = metadata

        if publish:
            self.last_status = "rendered"
        if send_to_frame:
            await self.async_send_to_frame(artifact.packed, artifact.crc32)
            self.last_status = "sent"
            self.last_metadata.pop(ATTR_LAST_ERROR, None)

        await self.async_save()
        return metadata

    async def async_render_moon(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        cache_provider_id: str | None = None,
    ) -> dict[str, Any]:
        from .moon_provider import build_moon_provider_data

        opts = self.options
        picked_location = data.get(CONF_WEATHER_LOCATION)
        if isinstance(picked_location, dict):
            latitude = str(picked_location.get(CONF_LATITUDE) or opts.get(CONF_LATITUDE) or "0")
            longitude = str(picked_location.get(CONF_LONGITUDE) or opts.get(CONF_LONGITUDE) or "0")
            location = str(data.get(CONF_LOCATION_NAME) or data.get("location") or opts.get(CONF_LOCATION_NAME) or "Home")
        else:
            latitude = str(data.get(CONF_LATITUDE) or opts.get(CONF_LATITUDE) or "0")
            longitude = str(data.get(CONF_LONGITUDE) or opts.get(CONF_LONGITUDE) or "0")
            location = str(data.get(CONF_LOCATION_NAME) or data.get("location") or opts.get(CONF_LOCATION_NAME) or "Home")

        render_target = self._time_sensitive_render_target(data)
        provider_data = build_moon_provider_data(
            latitude,
            longitude,
            location,
            self.hass.config.time_zone,
            current_datetime=render_target,
        )
        stem = self._provider_payload_name(cache_provider_id) if cache_provider_id else self.latest_payload_name
        artifact, card_data = await self.hass.async_add_executor_job(
            _render_moon_artifact_to_disk,
            provider_data,
            self.payload_dir,
            stem,
        )
        if cache_provider_id:
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.ppbin", self.payload_path())
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.preview.png", self.preview_path())

        metadata = dict(artifact.metadata)
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["render_target_at"] = render_target.isoformat()
        metadata["provider_id"] = "moon_phase"
        metadata["provider_name"] = "Moon Phase"
        metadata["card_renderer_version"] = CARD_RENDERER_VERSION
        metadata["source"] = "local_moon_calculation"
        metadata["source_name"] = "Ditherloom local moon calculation"
        metadata["source_url"] = ""
        metadata["attribution"] = card_data.attribution
        metadata["attribution_url"] = ""
        metadata["license"] = ""
        metadata["license_url"] = ""
        metadata["data_transformations"] = (
            "Moon phase, illumination, moonrise, moonset, and upcoming phase dates are calculated "
            "from configured coordinates and rendered into a Ditherloom e-ink card."
        )
        metadata["location"] = card_data.location
        metadata["date_label"] = card_data.date_label
        metadata["phase_name"] = card_data.phase_name
        metadata["illumination"] = card_data.illumination
        metadata["moon_age"] = card_data.moon_age
        metadata["moonrise"] = card_data.moonrise
        metadata["moonset"] = card_data.moonset
        metadata["next_full"] = card_data.next_full
        metadata["next_new"] = card_data.next_new
        metadata["primary_label"] = card_data.primary_label
        metadata["primary_value"] = card_data.primary_value
        metadata["secondary_prefix"] = card_data.secondary_prefix
        metadata["secondary_value"] = card_data.secondary_value
        metadata["update_interval_minutes"] = self._effective_update_interval_minutes()
        metadata["wake_window_seconds"] = self._effective_wake_window_seconds()
        metadata["wake_window_minutes"] = self._effective_wake_window_minutes()
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)
        metadata["content_rendered_at"] = metadata["rendered_at"]
        metadata["content_rendered_provider_id"] = metadata["provider_id"]
        metadata["content_rendered_provider_name"] = metadata["provider_name"]
        metadata["content_rendered_source_name"] = metadata["source_name"]
        metadata["content_rendered_attribution"] = metadata["attribution"]
        metadata["content_rendered_license"] = metadata["license"]
        metadata["content_rendered_content_id"] = metadata.get(ATTR_CONTENT_ID)
        metadata["content_rendered_crc32"] = metadata.get(ATTR_CRC32)
        for preserved_key in PRESERVED_RUNTIME_METADATA_KEYS:
            if preserved_key in self.last_metadata:
                metadata[preserved_key] = self.last_metadata[preserved_key]

        self.last_status = "rendered"
        self.last_metadata = metadata

        if publish:
            self.last_status = "rendered"
        if send_to_frame:
            await self.async_send_to_frame(artifact.packed, artifact.crc32)
            self.last_status = "sent"
            self.last_metadata.pop(ATTR_LAST_ERROR, None)

        await self.async_save()
        return metadata

    async def async_render_xkcd(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        cache_provider_id: str | None = None,
    ) -> dict[str, Any]:
        opts = self.options
        stem = self._provider_payload_name(cache_provider_id) if cache_provider_id else self.latest_payload_name
        render_data = {
            "xkcd_mode": opts.get(CONF_XKCD_MODE, DEFAULT_XKCD_MODE),
            "xkcd_number": opts.get(CONF_XKCD_NUMBER),
            "attempts": opts.get(CONF_XKCD_RANDOM_ATTEMPTS, DEFAULT_XKCD_RANDOM_ATTEMPTS),
        }
        render_data.update({key: value for key, value in data.items() if value not in (None, "")})
        artifact, comic, suitability = await self.hass.async_add_executor_job(
            _render_xkcd_artifact_to_disk,
            render_data,
            self.payload_dir,
            stem,
        )
        if cache_provider_id:
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.ppbin", self.payload_path())
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.preview.png", self.preview_path())

        metadata = dict(artifact.metadata)
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["provider_id"] = "xkcd_comic"
        metadata["provider_name"] = "xkcd Comic"
        metadata["card_renderer_version"] = CARD_RENDERER_VERSION
        metadata["source"] = "xkcd"
        metadata["source_name"] = "xkcd / Randall Munroe"
        metadata["source_url"] = comic.comic_url
        metadata["attribution"] = metadata.get("attribution") or "xkcd / Randall Munroe | CC BY-NC 2.5"
        metadata["attribution_url"] = "https://xkcd.com/license.html"
        metadata["license"] = "CC BY-NC 2.5"
        metadata["license_url"] = "https://creativecommons.org/licenses/by-nc/2.5/"
        metadata["data_transformations"] = metadata.get("data_transformations") or (
            "xkcd comic art is filtered for Ditherloom's 400x300 four-colour display, "
            "with unsuitable dense, tiny-detail, or poorly reproducible colour comics rejected."
        )
        metadata["xkcd_number"] = comic.number
        metadata["xkcd_title"] = comic.title
        metadata["xkcd_alt_text"] = comic.alt
        metadata["xkcd_image_url"] = comic.image_url
        metadata["xkcd_published"] = comic.published
        metadata["xkcd_mode"] = render_data.get("xkcd_mode", DEFAULT_XKCD_MODE)
        metadata["xkcd_configured_number"] = _positive_int(render_data.get("xkcd_number"))
        metadata["xkcd_random_attempts"] = _positive_int(render_data.get("attempts")) or DEFAULT_XKCD_RANDOM_ATTEMPTS
        metadata["xkcd_suitability"] = {
            "suitable": suitability.suitable,
            "score": suitability.score,
            "reasons": list(suitability.reasons),
            "warnings": list(suitability.warnings),
            "panel_count": suitability.panel_count,
            "aspect_ratio": suitability.aspect_ratio,
            "saturated_pixel_ratio": suitability.saturated_pixel_ratio,
            "safe_colour_pixel_ratio": suitability.safe_colour_pixel_ratio,
            "poor_colour_pixel_ratio": suitability.poor_colour_pixel_ratio,
            "dominant_poor_colour_families": list(suitability.dominant_poor_colour_families),
            "black_pixel_ratio": suitability.black_pixel_ratio,
            "ink_pixel_ratio": suitability.ink_pixel_ratio,
            "small_detail_pixel_ratio": suitability.small_detail_pixel_ratio,
            "fitted_art_size": list(suitability.fitted_art_size),
            "supported_features": list(suitability.supported_features),
            "unsupported_features": list(suitability.unsupported_features),
        }
        metadata["update_interval_minutes"] = self._effective_update_interval_minutes()
        metadata["wake_window_seconds"] = self._effective_wake_window_seconds()
        metadata["wake_window_minutes"] = self._effective_wake_window_minutes()
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)
        metadata["content_rendered_at"] = metadata["rendered_at"]
        metadata["content_rendered_provider_id"] = metadata["provider_id"]
        metadata["content_rendered_provider_name"] = metadata["provider_name"]
        metadata["content_rendered_source_name"] = metadata["source_name"]
        metadata["content_rendered_attribution"] = metadata["attribution"]
        metadata["content_rendered_license"] = metadata["license"]
        metadata["content_rendered_content_id"] = metadata.get(ATTR_CONTENT_ID)
        metadata["content_rendered_crc32"] = metadata.get(ATTR_CRC32)
        for preserved_key in PRESERVED_RUNTIME_METADATA_KEYS:
            if preserved_key in self.last_metadata:
                metadata[preserved_key] = self.last_metadata[preserved_key]

        self.last_status = "rendered"
        self.last_metadata = metadata

        if publish:
            self.last_status = "rendered"
        if send_to_frame:
            await self.async_send_to_frame(artifact.packed, artifact.crc32)
            self.last_status = "sent"
            self.last_metadata.pop(ATTR_LAST_ERROR, None)

        await self.async_save()
        return metadata

    def _effective_update_interval_minutes(self) -> int:
        return (
            _positive_int(self.options.get(CONF_FRAME_INTERVAL_MINUTES))
            or _positive_int(self.options.get(CONF_UPDATE_INTERVAL_MINUTES))
            or DEFAULT_UPDATE_INTERVAL_MINUTES
        )

    def _frame_interval_minutes(self) -> int | None:
        return _positive_int(self.options.get(CONF_FRAME_INTERVAL_MINUTES))

    def _effective_wake_window_seconds(self) -> int:
        opts = self.options
        return (
            _positive_int(opts.get(CONF_WAKE_WINDOW_SECONDS))
            or ((_positive_int(opts.get(CONF_WAKE_WINDOW_MINUTES)) or DEFAULT_WAKE_WINDOW_MINUTES) * 60)
        )

    def _effective_wake_window_minutes(self) -> int:
        seconds = self._effective_wake_window_seconds()
        return max(1, (seconds + 59) // 60)

    def _enabled_content_providers(self) -> list[str]:
        return enabled_content_providers(self.options)

    def _configured_ha_slots(self) -> list[int]:
        return ha_lane_slots(self.options)

    def _ha_owned_slots(self) -> list[int]:
        return self._configured_ha_slots()

    def _active_provider_slots(self) -> list[int]:
        try:
            return active_provider_slots(self.options)
        except ValueError:
            return self._configured_ha_slots()

    def _ha_slot_csv(self) -> str:
        return slot_csv(self._ha_owned_slots())

    def _reserved_ha_slot(self) -> int:
        slots = self._ha_owned_slots()
        return slots[0] if slots else int(self.options.get(CONF_TARGET_SLOT, DEFAULT_TARGET_SLOT))

    def _configured_reserved_slot(self) -> int:
        configured_slots = self._configured_ha_slots()
        if configured_slots:
            return configured_slots[0]
        return (
            _positive_int(self.options.get(CONF_FRAME_RESERVED_SLOT))
            or _positive_int(self.options.get(CONF_TARGET_SLOT))
            or DEFAULT_TARGET_SLOT
        )

    def _ha_slot_pool_text(self) -> str:
        slots = self._ha_owned_slots()
        return slot_csv(slots[1:]) if len(slots) > 1 else ""

    def _provider_slot_map(self) -> dict[str, int]:
        return provider_slot_map(self.options)

    def _selected_display_slot(self) -> int:
        return self._provider_slot_map()[self._selected_content_provider()]

    def _display_rotation_enabled(self) -> bool:
        enabled = _bool_option(
            self.options,
            CONF_FRAME_HA_ROTATION_ENABLED,
            _bool_option(self.options, CONF_HA_ROTATION_ENABLED, _bool_option(self.options, CONF_DISPLAY_ROTATION_ENABLED, False)),
        )
        return enabled and len(self._enabled_content_providers()) > 1

    def _display_rotation_interval_minutes(self) -> int:
        opts = self.options
        ha_seconds = _positive_int(opts.get(CONF_FRAME_HA_ROTATION_SECONDS, opts.get(CONF_HA_ROTATION_SECONDS)))
        if ha_seconds is not None:
            return max(1, (ha_seconds + 59) // 60)
        hours = _positive_int(opts.get(CONF_DISPLAY_ROTATION_HOURS))
        minutes = _positive_int(opts.get(CONF_DISPLAY_ROTATION_MINUTES))
        total = (hours or DEFAULT_DISPLAY_ROTATION_HOURS) * 60 + (minutes or 0)
        if total <= 0:
            total = DEFAULT_DISPLAY_ROTATION_MINUTES
        return total

    def _ha_rotation_enabled(self) -> bool:
        return _bool_option(
            self.options,
            CONF_FRAME_HA_ROTATION_ENABLED,
            _bool_option(self.options, CONF_HA_ROTATION_ENABLED, False),
        )

    def _ha_rotation_seconds(self) -> int:
        seconds = _positive_int(self.options.get(CONF_FRAME_HA_ROTATION_SECONDS, self.options.get(CONF_HA_ROTATION_SECONDS)))
        if seconds is not None:
            return max(60, seconds)
        legacy_minutes = self._display_rotation_interval_minutes()
        return max(60, legacy_minutes * 60)

    def _ha_rotation_config(self) -> dict[str, Any]:
        return {"enabled": self._ha_rotation_enabled(), "seconds": self._ha_rotation_seconds(), "slots": self._active_provider_slots()}

    def _time_sensitive_render_target(self, data: dict[str, Any] | None = None) -> datetime:
        explicit = _parse_datetime((data or {}).get("render_target_at") or (data or {}).get("renderTargetAt"))
        if explicit is not None:
            return explicit.astimezone(self._local_timezone())
        next_wake = _parse_datetime(self.last_metadata.get("frame_next_wake_at"))
        now_utc = datetime.now(timezone.utc)
        if next_wake is not None and next_wake.astimezone(timezone.utc) > now_utc:
            return next_wake.astimezone(self._local_timezone())
        return now_utc.astimezone(self._local_timezone())

    def _selected_content_provider(self) -> str:
        providers = self._enabled_content_providers()
        if not self._display_rotation_enabled():
            return providers[0]
        interval_seconds = max(60, self._display_rotation_interval_minutes() * 60)
        slot = int(datetime.now(timezone.utc).timestamp() // interval_seconds)
        return providers[slot % len(providers)]

    def _should_render_selected_content(self) -> bool:
        if not self.payload_path().exists() or ATTR_CRC32 not in self.last_metadata:
            return True
        selected = self._selected_content_provider()
        current = self.last_metadata.get("provider_id") or self.last_metadata.get("selected_provider_id")
        return current != selected

    def _provider_payload_name(self, provider: str | None) -> str:
        if provider == "sunrise_sunset":
            return "content-sunrise-sunset"
        if provider == "moon_phase":
            return "content-moon-phase"
        if provider == "xkcd_comic":
            return "content-xkcd"
        if provider == PROVIDER_DIESEL_SWEETIES:
            return "content-diesel-sweeties"
        if provider == PROVIDER_MIMI_EUNICE:
            return "content-mimi-eunice"
        if provider == PROVIDER_ASTROLOGY:
            return "content-daily-astrology"
        if provider == PROVIDER_ASTRONOMY_VISIBLE_PLANETS:
            return "content-astronomy-visible-planets"
        if provider == PROVIDER_ASTRONOMY_MOON_WATCH:
            return "content-astronomy-moon-watch"
        if provider == PROVIDER_ASTRONOMY_CONSTELLATION:
            return "content-astronomy-constellation"
        if provider == PROVIDER_ASTRONOMY_TONIGHT_SKY:
            return "content-astronomy-tonight-sky"
        if provider == PROVIDER_ASTRONOMY_OVERHEAD:
            return "content-astronomy-overhead"
        if provider == PROVIDER_ASTRONOMY_CONDITIONS:
            return "content-astronomy-conditions"
        if provider == PROVIDER_ASTRONOMY_SOLAR_ACTIVITY:
            return "content-astronomy-solar-activity"
        if provider == PROVIDER_ASTRONOMY_AURORA_WATCH:
            return "content-astronomy-aurora-watch"
        if provider == "open_meteo_weather":
            return "content-weather"
        if provider == PROVIDER_WEATHER_TODAY_TOMORROW:
            return "content-weather-today-tomorrow"
        if provider == PROVIDER_WEATHER_7_DAY:
            return "content-weather-7-day"
        if provider == PROVIDER_WEATHER_RADAR:
            return "content-weather-radar"
        if provider == PROVIDER_WEATHER_PRECIPITATION:
            return "content-weather-precipitation"
        if provider == PROVIDER_WEATHER_UV:
            return "content-weather-uv"
        if provider == PROVIDER_WEATHER_WIND:
            return "content-weather-wind"
        return self.latest_payload_name

    def _cached_metadata_path(self, provider: str) -> Path:
        return self.payload_dir / f"{self._provider_payload_name(provider)}.metadata.json"

    async def _write_cached_metadata(self, provider: str, metadata: dict[str, Any]) -> None:
        payload = dict(metadata)
        payload["cached_provider_id"] = provider
        payload["cached_at"] = datetime.now(timezone.utc).isoformat()
        path = self._cached_metadata_path(provider)
        await self.hass.async_add_executor_job(path.write_text, json.dumps(payload, indent=2), "utf-8")

    async def _read_cached_metadata(self, provider: str) -> dict[str, Any] | None:
        path = self._cached_metadata_path(provider)
        if not path.exists():
            return None
        try:
            text = await self.hass.async_add_executor_job(path.read_text, "utf-8")
            payload = json.loads(text)
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    def _cached_content_is_fresh(self, provider: str, metadata: dict[str, Any]) -> bool:
        if metadata.get("card_renderer_version") != CARD_RENDERER_VERSION:
            return False
        rendered_at = _parse_datetime(metadata.get("rendered_at"))
        if rendered_at is None:
            return False
        if provider in {PROVIDER_SUN, PROVIDER_MOON}:
            target = datetime.now(self._local_timezone())
            if metadata.get("date_label") != target.strftime("%d %b").upper():
                return False
            return True
        if provider == PROVIDER_XKCD:
            if not self._xkcd_cache_matches_options(metadata):
                return False
            if self._comic_cache_was_delivered(provider, metadata):
                return False
            mode = str(self.options.get(CONF_XKCD_MODE, DEFAULT_XKCD_MODE))
            if mode == XKCD_MODE_FIXED:
                return True
            age = datetime.now(timezone.utc) - rendered_at.astimezone(timezone.utc)
            return age < timedelta(minutes=self._effective_update_interval_minutes())
        if provider in COMIC_SUCCESSOR_PROVIDERS and self._comic_cache_was_delivered(provider, metadata):
            return False
        if provider == PROVIDER_ASTROLOGY:
            from .astrology_provider import normalize_signs

            if list(metadata.get("astrology_enabled_signs") or []) != normalize_signs(self.options.get(CONF_ASTROLOGY_SIGNS)):
                return False
            target = datetime.now(self._local_timezone())
            if metadata.get("astrology_date") != target.date().isoformat():
                return False
            from .astrology_provider import selected_sign_for_time

            current_sign = selected_sign_for_time(
                normalize_signs(self.options.get(CONF_ASTROLOGY_SIGNS)),
                target.replace(tzinfo=None),
                self._effective_update_interval_minutes(),
            )
            if metadata.get("astrology_sign") != current_sign:
                return False
            return True
        if provider in ASTRONOMY_PROVIDER_IDS:
            target = datetime.now(self._local_timezone())
            if metadata.get("astronomy_date") != target.date().isoformat():
                return False
            if metadata.get("astronomy_card_provider") != provider:
                return False
            return True
        age = datetime.now(timezone.utc) - rendered_at.astimezone(timezone.utc)
        return age < timedelta(minutes=self._effective_update_interval_minutes())

    def _xkcd_cache_matches_options(self, metadata: dict[str, Any]) -> bool:
        opts = self.options
        mode = str(opts.get(CONF_XKCD_MODE, DEFAULT_XKCD_MODE))
        if str(metadata.get("xkcd_mode", DEFAULT_XKCD_MODE)) != mode:
            return False
        configured_number = _positive_int(opts.get(CONF_XKCD_NUMBER))
        if _positive_int(metadata.get("xkcd_configured_number")) != configured_number:
            return False
        attempts = _positive_int(opts.get(CONF_XKCD_RANDOM_ATTEMPTS)) or DEFAULT_XKCD_RANDOM_ATTEMPTS
        if _positive_int(metadata.get("xkcd_random_attempts")) != attempts:
            return False
        return bool(metadata.get(ATTR_CONTENT_ID) and metadata.get(ATTR_CRC32))

    def _comic_cache_was_delivered(self, provider: str, metadata: dict[str, Any]) -> bool:
        if provider not in COMIC_SUCCESSOR_PROVIDERS:
            return False
        content_id = metadata.get(ATTR_CONTENT_ID)
        source_url = metadata.get("source_url")
        exclusions = self._comic_render_exclusion_data(provider)
        return bool(
            (content_id and content_id in exclusions.get("exclude_content_ids", []))
            or (source_url and source_url in exclusions.get("exclude_source_urls", []))
        )

    def _comic_render_exclusion_data(self, provider: str) -> dict[str, Any]:
        if provider not in COMIC_SUCCESSOR_PROVIDERS:
            return {}
        content_ids: list[str] = []
        source_urls: list[str] = []
        xkcd_numbers: list[int] = []

        def add_job(job: dict[str, Any]) -> None:
            if str(job.get("provider_id") or "") != provider:
                return
            content_id = str(job.get("content_id") or "").strip()
            source_url = str(job.get("source_url") or "").strip()
            if content_id and content_id not in content_ids:
                content_ids.append(content_id)
            if source_url and source_url not in source_urls:
                source_urls.append(source_url)
            if provider == PROVIDER_XKCD:
                number = _xkcd_number_from_url(source_url) or _xkcd_number_from_content_id(content_id)
                if number is not None and number not in xkcd_numbers:
                    xkcd_numbers.append(number)

        exclusions = self.last_metadata.get("comic_delivery_exclusions")
        if isinstance(exclusions, dict):
            provider_exclusions = exclusions.get(provider)
            if isinstance(provider_exclusions, dict):
                for content_id in provider_exclusions.get("content_ids") or []:
                    text = str(content_id).strip()
                    if text and text not in content_ids:
                        content_ids.append(text)
                for source_url in provider_exclusions.get("source_urls") or []:
                    text = str(source_url).strip()
                    if text and text not in source_urls:
                        source_urls.append(text)
                for number in provider_exclusions.get("xkcd_numbers") or []:
                    parsed = _positive_int(number)
                    if parsed is not None and parsed not in xkcd_numbers:
                        xkcd_numbers.append(parsed)

        for job in self.last_metadata.get("frame_awake_last_delivered_jobs") or []:
            if isinstance(job, dict):
                add_job(job)

        return {
            "exclude_content_ids": content_ids[-20:],
            "exclude_source_urls": source_urls[-20:],
            "exclude_xkcd_numbers": xkcd_numbers[-20:],
        }

    def _record_delivered_comic_exclusions(self, delivered_jobs: list[dict[str, Any]]) -> None:
        exclusions = dict(self.last_metadata.get("comic_delivery_exclusions") or {})
        for provider in COMIC_SUCCESSOR_PROVIDERS:
            current = dict(exclusions.get(provider) or {})
            content_ids = [str(value) for value in current.get("content_ids") or [] if str(value).strip()]
            source_urls = [str(value) for value in current.get("source_urls") or [] if str(value).strip()]
            xkcd_numbers = [
                number
                for value in current.get("xkcd_numbers") or []
                if (number := _positive_int(value)) is not None
            ]
            for job in delivered_jobs:
                if str(job.get("provider_id") or "") != provider:
                    continue
                content_id = str(job.get("content_id") or "").strip()
                source_url = str(job.get("source_url") or "").strip()
                if content_id and content_id not in content_ids:
                    content_ids.append(content_id)
                if source_url and source_url not in source_urls:
                    source_urls.append(source_url)
                if provider == PROVIDER_XKCD:
                    number = _xkcd_number_from_url(source_url) or _xkcd_number_from_content_id(content_id)
                    if number is not None and number not in xkcd_numbers:
                        xkcd_numbers.append(number)
            exclusions[provider] = {
                "content_ids": content_ids[-20:],
                "source_urls": source_urls[-20:],
                "xkcd_numbers": xkcd_numbers[-20:],
            }
        self.last_metadata["comic_delivery_exclusions"] = exclusions

    def _local_timezone(self):
        from zoneinfo import ZoneInfo

        try:
            return ZoneInfo(self.hass.config.time_zone or "UTC")
        except Exception:
            return timezone.utc

    async def _frame_sync_jobs(self) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        slot_map = self._provider_slot_map()
        unavailable: dict[str, str] = {}
        for provider in self._enabled_content_providers():
            metadata = await self._read_cached_metadata(provider)
            if metadata is None:
                unavailable[provider] = "missing"
                continue
            if not self._cached_content_is_fresh(provider, metadata):
                unavailable[provider] = "stale"
                continue
            if not self._provider_needs_frame_sync(provider, metadata):
                continue
            stem = self._provider_payload_name(provider)
            payload_path = self.payload_dir / f"{stem}.ppbin"
            if not payload_path.exists():
                unavailable[provider] = "payload_missing"
                continue
            packed = await self.hass.async_add_executor_job(payload_path.read_bytes)
            jobs.append(
                {
                    "provider_id": provider,
                    "provider_name": metadata.get("provider_name"),
                    "slot": slot_map[provider],
                    "packed": packed,
                    "crc32": str(metadata[ATTR_CRC32]),
                    "content_id": metadata.get(ATTR_CONTENT_ID),
                    "date_label": metadata.get("date_label"),
                    "content_source": metadata.get("source"),
                    "source_name": metadata.get("source_name"),
                    "source_url": metadata.get("source_url"),
                    "attribution": metadata.get("attribution"),
                    "attribution_url": metadata.get("attribution_url"),
                    "license": metadata.get("license"),
                    "license_url": metadata.get("license_url"),
                }
            )
        queued_states = {job["provider_id"]: "queued_for_delivery" for job in jobs}
        if unavailable:
            self.last_metadata["frame_awake_unavailable_providers"] = unavailable
            self.last_metadata["frame_awake_missing_cached_providers"] = [
                provider for provider, reason in unavailable.items() if reason in {"missing", "stale"}
            ]
            self.last_metadata["frame_awake_provider_delivery_states"] = {**unavailable, **queued_states}
            if not jobs:
                self.last_status = "content_prerender_required"
                self.last_metadata[ATTR_LAST_ERROR] = (
                    "No deliverable Home Assistant content is ready. Provider states: "
                    + ", ".join(f"{provider}={reason}" for provider, reason in unavailable.items())
                )
            await self.async_save()
        else:
            self.last_metadata.pop("frame_awake_unavailable_providers", None)
            self.last_metadata.pop("frame_awake_missing_cached_providers", None)
            self.last_metadata["frame_awake_provider_delivery_states"] = queued_states
        self.last_metadata["ha_owned_slots"] = slot_map
        return jobs

    def _provider_needs_frame_sync(self, provider: str, metadata: dict[str, Any]) -> bool:
        content_id = metadata.get(ATTR_CONTENT_ID)
        if content_id:
            return metadata.get("frame_synced_content_id") != content_id
        if metadata.get("frame_synced_crc32") != metadata.get(ATTR_CRC32):
            return True
        if provider in {"sunrise_sunset", "moon_phase"}:
            if metadata.get("frame_synced_date_label") != metadata.get("date_label"):
                return True
            return metadata.get("frame_synced_render_target_at") != metadata.get("render_target_at")
        return _parse_datetime(metadata.get("frame_synced_at")) is None

    async def _mark_provider_frame_synced(self, provider: str, crc32: str, synced_at: str) -> None:
        metadata = await self._read_cached_metadata(provider)
        if metadata is None:
            return
        metadata["frame_synced_at"] = synced_at
        metadata["frame_synced_crc32"] = crc32
        metadata["frame_synced_content_id"] = metadata.get(ATTR_CONTENT_ID)
        metadata["frame_synced_date_label"] = metadata.get("date_label") or datetime.now(self._local_timezone()).strftime("%d %b").upper()
        if provider in {"sunrise_sunset", "moon_phase"}:
            metadata["frame_synced_render_target_at"] = metadata.get("render_target_at")
        await self._write_cached_metadata(provider, metadata)

    async def _refresh_delivered_comic_successors(self, delivered_jobs: list[dict[str, Any]], synced_at: str) -> None:
        refreshed: list[str] = []
        failed: dict[str, str] = {}
        for job in delivered_jobs:
            provider = str(job.get("provider_id") or "")
            if provider not in COMIC_SUCCESSOR_PROVIDERS:
                continue
            previous_status = self.last_status
            previous_metadata = dict(self.last_metadata)
            delivered_content_id = job.get("content_id")
            delivered_crc32 = job.get("crc32")
            try:
                rendered_successor = await self.async_render_provider_to_cache(provider)
                self.last_status = previous_status
                self.last_metadata = self._preserve_current_runtime_metadata(previous_metadata)
                if (
                    rendered_successor.get(ATTR_CONTENT_ID) == delivered_content_id
                    or str(rendered_successor.get(ATTR_CRC32)) == str(delivered_crc32)
                ):
                    rendered_successor["frame_synced_at"] = synced_at
                    rendered_successor["frame_synced_crc32"] = delivered_crc32
                    rendered_successor["frame_synced_content_id"] = delivered_content_id
                    await self._write_cached_metadata(provider, rendered_successor)
                refreshed.append(provider)
            except Exception as exc:
                self.last_status = previous_status
                self.last_metadata = self._preserve_current_runtime_metadata(previous_metadata)
                failed[provider] = f"{type(exc).__name__}: {exc}"
        if refreshed or failed:
            self.last_metadata["comic_successor_refresh_last_at"] = datetime.now(timezone.utc).isoformat()
            self.last_metadata["comic_successor_refresh_providers"] = refreshed
            if failed:
                self.last_metadata["comic_successor_refresh_failed"] = failed
            else:
                self.last_metadata.pop("comic_successor_refresh_failed", None)
            await self.async_save()

    def _preserve_current_runtime_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        preserved = dict(metadata)
        for key in PRESERVED_RUNTIME_METADATA_KEYS:
            if key in self.last_metadata:
                preserved[key] = self.last_metadata[key]
        return preserved

    def _time_sensitive_cache_minutes(self) -> int:
        return max(1, self._effective_update_interval_minutes() + self._effective_wake_window_minutes())

    def async_cancel_weather_refresh(self) -> None:
        if self._weather_refresh_unsub:
            self._weather_refresh_unsub()
            self._weather_refresh_unsub = None

    def async_cancel_astrology_daily_refresh(self) -> None:
        if self._astrology_daily_refresh_unsub:
            self._astrology_daily_refresh_unsub()
            self._astrology_daily_refresh_unsub = None

    def _schedule_weather_refresh(self) -> None:
        interval_minutes = self._effective_update_interval_minutes()
        interval = timedelta(minutes=interval_minutes)
        self.async_cancel_weather_refresh()
        self.last_metadata["weather_refresh_interval_minutes"] = interval_minutes
        self.last_metadata["weather_refresh_next_at"] = (datetime.now(timezone.utc) + interval).isoformat()
        self._weather_refresh_unsub = async_track_time_interval(self.hass, self._handle_weather_refresh, interval)

    def _schedule_astrology_daily_refresh(self) -> None:
        self.async_cancel_astrology_daily_refresh()
        now = datetime.now(self._local_timezone())
        next_at = now.replace(hour=0, minute=2, second=0, microsecond=0)
        if next_at <= now:
            next_at = next_at + timedelta(days=1)
        self.last_metadata["astrology_daily_refresh_next_at"] = next_at.isoformat()
        self._astrology_daily_refresh_unsub = async_track_point_in_time(
            self.hass,
            self._handle_astrology_daily_refresh,
            next_at.astimezone(timezone.utc),
        )

    async def _handle_astrology_daily_refresh(self, now: datetime) -> None:
        try:
            if PROVIDER_ASTROLOGY in self._enabled_content_providers():
                await self.async_render_provider_to_cache(PROVIDER_ASTROLOGY)
                self.last_metadata["astrology_daily_refresh_last_at"] = now.isoformat()
                await self.async_save()
        except Exception as exc:
            self.last_status = "astrology_daily_refresh_failed"
            self.last_metadata[ATTR_LAST_ERROR] = f"Daily Astrology refresh failed: {type(exc).__name__}: {exc}"
            self.last_metadata["astrology_daily_refresh_last_failed_at"] = now.isoformat()
            await self.async_save()
        finally:
            self._schedule_astrology_daily_refresh()

    async def _handle_weather_refresh(self, now: datetime) -> None:
        if self._weather_refresh_running:
            return
        self._weather_refresh_running = True
        try:
            await self.async_refresh_weather_payload(reason="timer")
        except Exception as exc:
            self.last_status = "content_refresh_failed"
            self.last_metadata[ATTR_LAST_ERROR] = f"Content refresh failed: {type(exc).__name__}: {exc}"
            self.last_metadata["content_refresh_last_failed_at"] = now.isoformat()
            self._create_notification("Ditherloom content refresh failed", str(self.last_metadata[ATTR_LAST_ERROR]))
            await self.async_save()
        finally:
            self._weather_refresh_running = False

    def _create_notification(self, title: str, message: str) -> None:
        if not self.hass.services.has_service("persistent_notification", "create"):
            return
        self.hass.async_create_task(
            self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"{DOMAIN}_{self.entry.entry_id}_sync",
                },
                blocking=False,
            )
        )

    @property
    def preview_url(self) -> str:
        return f"/api/ditherloom/{self.entry.entry_id}/preview/{self.latest_payload_name}.preview.png"

    def provider_preview_url(self, provider: str) -> str:
        return f"/api/ditherloom/{self.entry.entry_id}/preview/{self._provider_payload_name(provider)}.preview.png"

    @property
    def frame_awake_url(self) -> str:
        return f"/api/ditherloom/{self.entry.entry_id}/frame-awake"

    @property
    def frame_sleeping_url(self) -> str:
        return f"/api/ditherloom/{self.entry.entry_id}/frame-sleeping"

    def app_discovery_payload(self, origin: str) -> dict[str, Any]:
        origin = origin.rstrip("/")
        options = self.options
        callback_base_path = f"/api/ditherloom/{self.entry.entry_id}"
        frame_awake_url = f"{origin}{self.frame_awake_url}"
        frame_sleeping_url = f"{origin}{self.frame_sleeping_url}"
        return {
            "accepted": True,
            "integrationInstalled": True,
            "integrationDomain": DOMAIN,
            "integration_domain": DOMAIN,
            "integrationName": "Ditherloom Suite Home Assistant Add On",
            "entryId": self.entry.entry_id,
            "entry_id": self.entry.entry_id,
            "libraryId": self.entry.data.get("library_id"),
            "haUrl": origin,
            "ha_url": origin,
            "discovery_requires_auth": True,
            "version": _integration_version(),
            "callbackBasePath": callback_base_path,
            "frameAwakePath": self.frame_awake_url,
            "frameSleepingPath": self.frame_sleeping_url,
            "frameAwakeUrl": frame_awake_url,
            "frameSleepingUrl": frame_sleeping_url,
            "frame_awake_url": frame_awake_url,
            "frame_sleeping_url": frame_sleeping_url,
            "reservedSlot": self._configured_reserved_slot(),
            "haSlotPool": self._ha_slot_pool_text(),
            "haSlotCsv": self._ha_slot_csv(),
            "intervalMinutes": self._frame_interval_minutes(),
            "wakeWindowSeconds": self._effective_wake_window_seconds(),
            "haRotationEnabled": self._ha_rotation_enabled(),
            "haRotationSeconds": self._ha_rotation_seconds(),
            "haRotationStatus": self.last_metadata.get("ha_rotation"),
            "previewPath": self.preview_url,
            "previewUrl": f"{origin}{self.preview_url}",
            "config": {
                "schema": "ditherloom-ha-config-v1",
                "haUrl": origin,
                "integrationDomain": DOMAIN,
                "integrationInstalled": True,
                "entryId": self.entry.entry_id,
                "callbackBasePath": callback_base_path,
                "frameAwakePath": self.frame_awake_url,
                "frameSleepingPath": self.frame_sleeping_url,
                "intervalMinutes": self._frame_interval_minutes(),
                "wakeWindowSeconds": self._effective_wake_window_seconds(),
                "maxJobsPerWake": options.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE),
                "reservedSlot": self._configured_reserved_slot(),
                "haSlotPool": self._ha_slot_pool_text(),
                "haSlotCsv": self._ha_slot_csv(),
                "haOwnedSlots": self._ha_owned_slots(),
                "haRotationEnabled": self._ha_rotation_enabled(),
                "haRotationSeconds": self._ha_rotation_seconds(),
                "scheduleEnabled": True,
                "sleepAfterEmpty": True,
                "sleepAfterJob": True,
                "libraryId": self.entry.data.get("library_id"),
                "topicBase": options.get(CONF_TOPIC_BASE) or f"ditherloom/{self.entry.data.get('library_id')}",
            },
        }

    def payload_path(self) -> Path:
        return self.payload_dir / f"{self.latest_payload_name}.ppbin"

    def preview_path(self) -> Path:
        return self.payload_dir / f"{self.latest_payload_name}.preview.png"

    async def async_send_to_frame(self, packed: bytes, crc32: str) -> None:
        host = self.options.get(CONF_FRAME_HOST)
        port = int(self.options.get(CONF_FRAME_PORT, DEFAULT_FRAME_PORT))
        if not host:
            raise ValueError("Frame host is not configured")
        target_slot = self._reserved_ha_slot()
        await self.async_send_to_frame_host(host, port, packed, crc32, target_slot)

    async def async_send_to_frame_host(self, host: str, port: int, packed: bytes, crc32: str, target_slot: int) -> None:
        if not host:
            raise ValueError("Frame host is not configured")
        if target_slot < 1 or target_slot > DEVICE_SLOT_COUNT:
            raise ValueError(f"Frame target slot {target_slot} is outside the supported slot range")
        await self.hass.async_add_executor_job(_send_existing_gateway_job, host, port, packed, crc32, target_slot)


def _integration_version() -> str:
    return INTEGRATION_VERSION


async def _validate_discovery_bearer_token(hass: HomeAssistant, request, body: dict[str, Any] | None = None) -> bool:
    auth_header = str(request.headers.get("Authorization", "")).strip()
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = str(request.headers.get("X-Home-Assistant-Token", "")).strip()
    if not token and body:
        token = str(body.get("haAccessToken") or body.get("accessToken") or "").strip()
    if not token:
        return False
    validator = getattr(getattr(hass, "auth", None), "async_validate_access_token", None)
    if validator is None:
        return False
    try:
        result = validator(token)
        if inspect.isawaitable(result):
            result = await result
        return result is not None
    except Exception:
        return False


class DitherloomDiscoveryView(HomeAssistantView):
    requires_auth = False
    url = "/api/ditherloom/discovery"
    extra_urls = [
        "/api/ditherloom/register-frame",
        "/api/ditherloom/discover-frame",
    ]
    name = f"api:{DOMAIN}:discovery"

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request):
        return await self._handle(request, {})

    async def post(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        if body is None:
            body = {}
        if not isinstance(body, dict):
            return self.json({"error": "JSON body must be an object"}, status_code=400)
        return await self._handle(request, body)

    async def _handle(self, request, body: dict[str, Any]):
        if not await _validate_discovery_bearer_token(self.hass, request, body):
            return self.json(
                {
                    "accepted": False,
                    "error": "unauthorized",
                    "message": DISCOVERY_AUTH_MESSAGE,
                },
                status_code=401,
            )
        runtimes = list(self.hass.data.get(DOMAIN, {}).values())
        library_id = str(body.get("library_id") or body.get("libraryId") or request.query.get("library_id") or "").strip()
        if library_id:
            runtimes = [
                runtime
                for runtime in runtimes
                if str(runtime.entry.data.get("library_id") or "").lower() == library_id.lower()
            ]
        if not runtimes:
            return self.json(
                {
                    "accepted": False,
                    "integrationInstalled": True,
                    "integrationDomain": DOMAIN,
                    "integration_domain": DOMAIN,
                    "error": "not_configured",
                    "message": "Ditherloom integration is installed but no config entry is available.",
                },
                status_code=404,
            )
        if len(runtimes) > 1:
            return self.json(
                {
                    "accepted": False,
                    "integrationInstalled": True,
                    "integrationDomain": DOMAIN,
                    "integration_domain": DOMAIN,
                    "error": "multiple_entries",
                    "message": "Multiple Ditherloom integration entries are configured; include library_id.",
                    "entries": [
                        {
                            "entryId": runtime.entry.entry_id,
                            "entry_id": runtime.entry.entry_id,
                            "libraryId": runtime.entry.data.get("library_id"),
                        }
                        for runtime in runtimes
                    ],
                },
                status_code=409,
            )

        origin = f"{request.scheme}://{request.host}"
        runtime = runtimes[0]
        await _store_frame_provided_ha_config(self.hass, runtime.entry, body)
        runtime.last_metadata["frame_ha_config"] = _frame_provided_ha_config(runtime.options)
        await runtime.async_save()
        return self.json(runtime.app_discovery_payload(origin))


async def _store_frame_provided_ha_config(hass: HomeAssistant, entry: ConfigEntry, body: dict[str, Any]) -> None:
    updates: dict[str, Any] = {}
    if "reservedSlot" in body:
        reserved = _positive_int(body.get("reservedSlot"))
        if reserved is not None:
            updates[CONF_FRAME_RESERVED_SLOT] = reserved
    if "haSlotPool" in body:
        updates[CONF_FRAME_HA_SLOT_POOL] = str(body.get("haSlotPool") or "").strip()
    if "haSlotCsv" in body:
        updates[CONF_FRAME_HA_SLOT_CSV] = slot_csv(sorted(parse_slot_pool(body.get("haSlotCsv"))))
    elif updates.get(CONF_FRAME_RESERVED_SLOT) is not None:
        slots = [updates[CONF_FRAME_RESERVED_SLOT]]
        for slot in parse_slot_pool(updates.get(CONF_FRAME_HA_SLOT_POOL, "")):
            if slot not in slots:
                slots.append(slot)
        updates[CONF_FRAME_HA_SLOT_CSV] = slot_csv(sorted(slots))
    if "haRotationEnabled" in body:
        updates[CONF_FRAME_HA_ROTATION_ENABLED] = bool(body.get("haRotationEnabled"))
    if "haRotationSeconds" in body:
        seconds = _positive_int(body.get("haRotationSeconds"))
        if seconds is not None:
            updates[CONF_FRAME_HA_ROTATION_SECONDS] = seconds
    if "intervalMinutes" in body:
        interval_minutes = _positive_int(body.get("intervalMinutes"))
        if interval_minutes is not None:
            updates[CONF_FRAME_INTERVAL_MINUTES] = interval_minutes
    if "wakeWindowSeconds" in body:
        wake_window_seconds = _positive_int(body.get("wakeWindowSeconds"))
        if wake_window_seconds is not None:
            updates[CONF_WAKE_WINDOW_SECONDS] = wake_window_seconds
    if not updates:
        return
    options = {**entry.options, **updates}
    hass.config_entries.async_update_entry(entry, options=options)


def _frame_provided_ha_config(options: dict[str, Any]) -> dict[str, Any]:
    configured_slots = ha_lane_slots(options)
    try:
        active_slots = active_provider_slots(options)
    except ValueError:
        active_slots = configured_slots
    slots = configured_slots
    reserved = slots[0] if slots else _positive_int(options.get(CONF_FRAME_RESERVED_SLOT))
    return {
        "reservedSlot": reserved,
        "haSlotPool": slot_csv(slots[1:]) if len(slots) > 1 else "",
        "haSlotCsv": slot_csv(slots),
        "configuredHaSlotCsv": slot_csv(configured_slots),
        "activeProviderSlotCsv": slot_csv(active_slots),
        "intervalMinutes": _positive_int(options.get(CONF_FRAME_INTERVAL_MINUTES)),
        "haRotationEnabled": _bool_option(options, CONF_FRAME_HA_ROTATION_ENABLED, False),
        "haRotationSeconds": _positive_int(options.get(CONF_FRAME_HA_ROTATION_SECONDS)) or DEFAULT_HA_ROTATION_SECONDS,
        "wakeWindowSeconds": _positive_int(options.get(CONF_WAKE_WINDOW_SECONDS)),
    }


class DitherloomPreviewView(HomeAssistantView):
    requires_auth = False

    def __init__(self, runtime: DitherloomRuntime) -> None:
        self.runtime = runtime
        self.url = f"/api/ditherloom/{runtime.entry.entry_id}/preview/{{filename}}"
        self.name = f"api:{DOMAIN}:preview:{runtime.entry.entry_id}"

    async def get(self, request, filename: str):
        if not filename.endswith(".preview.png") or "/" in filename or "\\" in filename:
            return self.json({"error": "not_found"}, status_code=404)
        path = self.runtime.payload_dir / filename
        active_path = self.runtime.preview_path()
        if filename == active_path.name:
            path = active_path
        if not path.exists():
            return self.json({"error": "not_found"}, status_code=404)
        return web.FileResponse(
            path,
            headers={
                "Content-Type": "image/png",
                "Cache-Control": "no-store",
            },
        )


class DitherloomComicSampleView(HomeAssistantView):
    requires_auth = False

    def __init__(self, runtime: DitherloomRuntime) -> None:
        self.runtime = runtime
        self.url = f"/api/ditherloom/{runtime.entry.entry_id}/comic-samples/{{filename}}"
        self.name = f"api:{DOMAIN}:comic_samples:{runtime.entry.entry_id}"

    async def get(self, request, filename: str):
        if not filename.endswith(".preview.png") or "/" in filename or "\\" in filename:
            return self.json({"error": "not_found"}, status_code=404)
        path = Path(__file__).resolve().parent / "assets" / "comic_samples" / filename
        if not path.exists():
            return self.json({"error": "not_found"}, status_code=404)
        return web.FileResponse(
            path,
            headers={
                "Content-Type": "image/png",
                "Cache-Control": "no-store",
            },
        )


class DitherloomWeatherSampleView(HomeAssistantView):
    requires_auth = False

    def __init__(self, runtime: DitherloomRuntime) -> None:
        self.runtime = runtime
        self.url = f"/api/ditherloom/{runtime.entry.entry_id}/weather-samples/{{filename}}"
        self.name = f"api:{DOMAIN}:weather_samples:{runtime.entry.entry_id}"

    async def get(self, request, filename: str):
        if not filename.endswith(".preview.png") or "/" in filename or "\\" in filename:
            return self.json({"error": "not_found"}, status_code=404)
        path = Path(__file__).resolve().parent / "assets" / "weather_samples" / filename
        if not path.exists():
            return self.json({"error": "not_found"}, status_code=404)
        return web.FileResponse(
            path,
            headers={
                "Content-Type": "image/png",
                "Cache-Control": "no-store",
            },
        )


class DitherloomFrameAwakeView(HomeAssistantView):
    requires_auth = False

    def __init__(self, runtime: DitherloomRuntime) -> None:
        self.runtime = runtime
        self.url = f"/api/ditherloom/{runtime.entry.entry_id}/frame-awake"
        self.name = f"api:{DOMAIN}:frame_awake:{runtime.entry.entry_id}"

    async def post(self, request):
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("JSON body must be an object")
            response = await self.runtime.async_handle_frame_awake(body, request.remote)
            return self.json(response)
        except Exception as exc:
            return self.json(
                {"accepted": False, "error": f"{type(exc).__name__}: {exc}"},
                status_code=400,
            )


class DitherloomFrameSleepingView(HomeAssistantView):
    requires_auth = False

    def __init__(self, runtime: DitherloomRuntime) -> None:
        self.runtime = runtime
        self.url = f"/api/ditherloom/{runtime.entry.entry_id}/frame-sleeping"
        self.name = f"api:{DOMAIN}:frame_sleeping:{runtime.entry.entry_id}"

    async def post(self, request):
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("JSON body must be an object")
            response = await self.runtime.async_handle_frame_sleeping(body, request.remote)
            return self.json(response)
        except Exception as exc:
            return self.json(
                {"accepted": False, "error": f"{type(exc).__name__}: {exc}"},
                status_code=400,
            )


def _readline(sock_file) -> str:
    line = sock_file.readline()
    if not line:
        raise RuntimeError("Frame closed Gateway connection")
    return line.decode("utf-8", errors="replace").strip()


WIFI_BANNER_PREFIX = "OK " + "PIC" + "PAK" + " WIFI"


def _send_command(sock_file, command: str) -> str:
    sock_file.write((command + "\n").encode("utf-8"))
    sock_file.flush()
    response = _readline(sock_file)
    # The Wi-Fi Gateway announces itself immediately after TCP connect. If that
    # banner is left in the stream, every command response is read one line late.
    if response.startswith(WIFI_BANNER_PREFIX):
        response = _readline(sock_file)
    return response


def _send_existing_gateway_job(host: str, port: int, packed: bytes, crc32: str, slot: int) -> None:
    _send_gateway_batch_jobs(host, port, [{"slot": slot, "packed": packed, "crc32": crc32}], slot, None)


def _send_gateway_batch_jobs(
    host: str,
    port: int,
    jobs: list[dict[str, Any]],
    display_slot: int | None,
    ha_rotation: dict[str, Any] | None,
) -> dict[str, Any]:
    if not jobs and display_slot is None and not ha_rotation:
        return {}
    for job in jobs:
        packed = job["packed"]
        slot = int(job["slot"])
        if len(packed) != DEVICE_PACKED_PAYLOAD_BYTES:
            raise ValueError(f"Packed payload must be exactly {DEVICE_PACKED_PAYLOAD_BYTES} bytes, got {len(packed)}")
        if slot < 1 or slot > DEVICE_SLOT_COUNT:
            raise ValueError(f"Target slot must be between 1 and {DEVICE_SLOT_COUNT}, got {slot}")
    if display_slot is not None and (display_slot < 1 or display_slot > DEVICE_SLOT_COUNT):
        raise ValueError(f"Display slot must be between 1 and {DEVICE_SLOT_COUNT}, got {display_slot}")
    ha_rotation_enabled = bool(ha_rotation and ha_rotation.get("enabled"))
    ha_rotation_slots = sorted(set(int(slot) for slot in (ha_rotation or {}).get("slots", [])))
    for slot in ha_rotation_slots:
        if slot < 1 or slot > DEVICE_SLOT_COUNT:
            raise ValueError(f"HA rotation slot must be between 1 and {DEVICE_SLOT_COUNT}, got {slot}")
    with socket.create_connection((host, port), timeout=20) as sock:
        sock.settimeout(30)
        sock_file = sock.makefile("rwb")
        gateway_status: dict[str, Any] = {}
        try:
            pong = _send_gateway_stage(sock_file, "PING", "PING")
            if not pong.startswith("OK"):
                raise RuntimeError(f"PING failed: {pong}")
            gateway_status["ha_rotation"] = _query_gateway_ha_rotation(sock_file)
            for job in jobs:
                slot = int(job["slot"])
                packed = job["packed"]
                crc32 = str(job["crc32"])
                _upload_gateway_payload(sock_file, slot, packed, crc32)
                _ensure_gateway_slot_is_ha(sock_file, slot)
            if ha_rotation_enabled:
                rotation_seconds = int((ha_rotation or {}).get("seconds") or DEFAULT_HA_ROTATION_SECONDS)
                if not _harotation_state_matches(gateway_status["ha_rotation"], rotation_seconds, ha_rotation_slots):
                    _set_gateway_ha_rotation(sock_file, rotation_seconds, ha_rotation_slots)
                display_slot = None
            if display_slot is not None:
                _ensure_gateway_slot_is_ha(sock_file, display_slot)
                display = _send_gateway_stage(sock_file, f"DISPLAY {display_slot}", "DISPLAY")
                if not display.startswith("OK"):
                    raise RuntimeError(f"DISPLAY failed: {display}")
            gateway_status["ha_completion"] = _send_gateway_completion(sock_file)
        except Exception:
            _best_effort_open_connection_idle(sock_file)
            raise
        return gateway_status


def _ensure_gateway_slot_is_ha(sock_file, slot: int) -> None:
    marked = _send_gateway_stage(sock_file, f"SETSLOTCLASS {slot} ha", "SETSLOTCLASS")
    if not marked.startswith("OK"):
        raise RuntimeError(f"SETSLOTCLASS failed for slot {slot}: {marked}")
    response = _send_gateway_stage(sock_file, f"SLOTCLASS {slot}", "SLOTCLASS")
    if not response.startswith("OK"):
        raise RuntimeError(f"SLOTCLASS failed for slot {slot}: {response}")
    normalized = response.lower()
    has_ha_class = "class=ha" in normalized or "value=3" in normalized
    excluded_from_rotation = "rotation_selectable=0" in normalized
    if not has_ha_class or not excluded_from_rotation:
        raise RuntimeError(f"Slot {slot} is not confirmed as HA-owned: {response}")


def _query_gateway_ha_rotation(sock_file) -> dict[str, Any]:
    response = _send_gateway_stage(sock_file, "HAROTATION", "HAROTATION")
    parsed = _parse_harotation_response(response)
    if parsed:
        return parsed
    return {"raw": response, "reachable": True}


def _parse_harotation_response(response: str) -> dict[str, Any]:
    normalized = response.strip()
    if not normalized.startswith("OK HAROTATION"):
        return {}
    parsed: dict[str, Any] = {"raw": normalized, "reachable": True}
    for part in normalized.split()[2:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parsed[key] = value
    parsed["enabled"] = str(parsed.get("enabled", "0")) == "1"
    parsed["seconds"] = _positive_int(parsed.get("seconds")) or 0
    parsed["slots"] = parse_slot_pool(parsed.get("slots", ""))
    parsed["normal_rotation"] = parsed.get("normal_rotation")
    return parsed


def _set_gateway_ha_rotation(sock_file, seconds: int, slots: list[int]) -> None:
    if not slots:
        raise RuntimeError("HA rotation requires at least one HA-owned slot")
    for slot in slots:
        _ensure_gateway_slot_is_ha(sock_file, slot)
    command = f"HAROTATION on {max(60, int(seconds))} {slot_csv(slots)}"
    response = _send_gateway_stage(sock_file, command, "HAROTATION")
    if not _harotation_on_response_ok(response, seconds, slots):
        raise RuntimeError(f"HAROTATION failed or firmware rejected HA rotation slots: {response}")


def _harotation_state_matches(state: dict[str, Any], seconds: int, slots: list[int]) -> bool:
    return (
        bool(state.get("enabled"))
        and int(state.get("seconds") or 0) == max(60, int(seconds))
        and list(state.get("slots") or []) == slots
    )


def _harotation_on_response_ok(response: str, seconds: int, slots: list[int]) -> bool:
    normalized = response.strip()
    if not normalized.startswith("OK HAROTATION"):
        return False
    required = (
        "enabled=1",
        f"seconds={max(60, int(seconds))}",
        f"count={len(slots)}",
        f"slots={slot_csv(slots)}",
    )
    return all(token in normalized for token in required)


def _upload_gateway_payload(sock_file, slot: int, packed: bytes, crc32: str) -> None:
    if len(packed) != DEVICE_PACKED_PAYLOAD_BYTES:
        raise ValueError(f"Packed payload must be exactly {DEVICE_PACKED_PAYLOAD_BYTES} bytes, got {len(packed)}")
    if slot < 1 or slot > DEVICE_SLOT_COUNT:
        raise ValueError(f"Target slot must be between 1 and {DEVICE_SLOT_COUNT}, got {slot}")

    begin = _send_gateway_stage(sock_file, f"BEGIN {slot} {len(packed)} 0x{crc32}", "BEGIN")
    if not begin.startswith("OK"):
        raise RuntimeError(f"BEGIN failed: {begin}")
    offset = 0
    while offset < len(packed):
        chunk = packed[offset : offset + DEVICE_WIFI_B64WRITE_CHUNK_BYTES]
        encoded = base64.b64encode(chunk).decode("ascii")
        command = f"B64WRITE {slot} {offset} {encoded}"
        if len(command) > DEVICE_WIFI_COMMAND_MAX_CHARS:
            raise ValueError(f"B64WRITE command exceeds {DEVICE_WIFI_COMMAND_MAX_CHARS} characters")
        response = _send_gateway_stage(sock_file, command, f"B64WRITE offset={offset}")
        if not response.startswith("OK"):
            raise RuntimeError(
                f"B64WRITE failed at {offset}: {response} "
                f"slot={slot} chunk_bytes={len(chunk)} command_chars={len(command)}"
            )
        offset += len(chunk)
    end = _send_gateway_stage(sock_file, f"END {slot}", "END")
    if not end.startswith("OK"):
        raise RuntimeError(f"END failed: {end}")


def _send_gateway_stage(sock_file, command: str, stage: str) -> str:
    try:
        return _send_command(sock_file, command)
    except TimeoutError as exc:
        raise TimeoutError(f"timed out during Gateway {stage}") from exc
    except OSError as exc:
        raise RuntimeError(f"Gateway {stage} failed: {type(exc).__name__}: {exc}") from exc


def _send_gateway_completion(sock_file) -> dict[str, Any]:
    command = "HACOMPLETE all_jobs_complete"
    sent_at = datetime.now(timezone.utc).isoformat()
    response = _send_gateway_stage(sock_file, command, "HACOMPLETE all_jobs_complete")
    ok = response.startswith("OK HACOMPLETE")
    if not ok:
        raise RuntimeError(f"HACOMPLETE all_jobs_complete failed: {response}")
    return {
        "command": command,
        "sent_at": sent_at,
        "response": response,
        "ok": ok,
    }


def _best_effort_open_connection_idle(sock_file) -> None:
    try:
        _send_command(sock_file, "IDLE")
    except Exception:
        pass


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _xkcd_number_from_url(value: Any) -> int | None:
    text = str(value or "")
    match = re.search(r"xkcd\.com/(\d+)/?", text)
    if not match:
        return None
    return _positive_int(match.group(1))


def _xkcd_number_from_content_id(value: Any) -> int | None:
    text = str(value or "")
    match = re.search(r"xkcd_(\d+)", text)
    if not match:
        return None
    return _positive_int(match.group(1))


def _bool_option(data: dict[str, Any], key: str, default: bool) -> bool:
    return bool(data[key]) if key in data else default


def _fetch_openweather_radar_snapshot(
    latitude: str,
    longitude: str,
    api_key: str,
    layer: str,
    zoom: int,
    cache_dir: Path | None = None,
) -> bytes:
    from io import BytesIO

    from PIL import Image, ImageDraw

    lat = max(-85.05112878, min(85.05112878, float(latitude)))
    lon = ((float(longitude) + 180.0) % 360.0) - 180.0
    zoom = max(3, min(8, int(zoom)))
    layer = layer if layer in {"precipitation_new", "clouds_new", "wind_new", "temp_new"} else "precipitation_new"
    tile_count = 2**zoom
    world_x = (lon + 180.0) / 360.0 * tile_count * 256
    lat_rad = math.radians(lat)
    world_y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * tile_count * 256
    tile_x = int(world_x // 256)
    tile_y = int(world_y // 256)
    offset_x = int(world_x - tile_x * 256)
    offset_y = int(world_y - tile_y * 256)
    base_canvas = Image.new("RGB", (768, 768), (231, 229, 208))
    overlay_canvas = Image.new("RGBA", (768, 768), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base_canvas)
    for grid in range(0, 769, 64):
        draw.line((grid, 0, grid, 768), fill=(198, 196, 176), width=1)
        draw.line((0, grid, 768, grid), fill=(198, 196, 176), width=1)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            x = (tile_x + dx) % tile_count
            y = max(0, min(tile_count - 1, tile_y + dy))
            base_tile = _fetch_osm_basemap_tile(zoom, x, y, cache_dir)
            if base_tile is not None:
                base_canvas.paste(base_tile, ((dx + 1) * 256, (dy + 1) * 256))
            tile = _fetch_openweather_tile(layer, zoom, x, y, api_key)
            if tile is not None:
                overlay_canvas.alpha_composite(tile, ((dx + 1) * 256, (dy + 1) * 256))
    center_x = 256 + offset_x
    center_y = 256 + offset_y
    crop_box = (center_x - 128, center_y - 128, center_x + 128, center_y + 128)
    crop = base_canvas.crop(crop_box).convert("RGBA")
    overlay = overlay_canvas.crop(crop_box)
    crop_pixels = crop.load()
    overlay_pixels = overlay.load()
    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b, a = overlay_pixels[x, y]
            if a >= 12:
                crop_pixels[x, y] = (r, g, b, min(254, max(24, a)))
    output = BytesIO()
    crop.save(output, format="PNG")
    return output.getvalue()


def _fetch_openweather_tile(layer: str, zoom: int, x: int, y: int, api_key: str) -> Any:
    from io import BytesIO

    from PIL import Image

    params = urllib.parse.urlencode({"appid": api_key})
    url = f"https://tile.openweathermap.org/map/{layer}/{zoom}/{x}/{y}.png?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": f"Ditherloom/{INTEGRATION_VERSION}"})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = response.read(1_000_000)
    except Exception:
        return None
    return Image.open(BytesIO(payload)).convert("RGBA")


def _fetch_osm_basemap_tile(zoom: int, x: int, y: int, cache_dir: Path | None) -> Any:
    from io import BytesIO

    from PIL import Image, ImageEnhance

    cache_path: Path | None = None
    if cache_dir is not None:
        cache_path = cache_dir / "osm" / str(zoom) / str(x) / f"{y}.png"
        try:
            if cache_path.exists() and datetime.now(timezone.utc).timestamp() - cache_path.stat().st_mtime < 7 * 24 * 60 * 60:
                return Image.open(cache_path).convert("RGB")
        except Exception:
            pass
    url = f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"Ditherloom/{INTEGRATION_VERSION} Home Assistant radar basemap",
            "Referer": "https://github.com/nacameron/ditherloom-suite-home-assistant-add-on",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = response.read(1_000_000)
    except Exception:
        return None
    image = Image.open(BytesIO(payload)).convert("RGB")
    image = ImageEnhance.Color(image).enhance(0.45)
    image = ImageEnhance.Contrast(image).enhance(0.82)
    image = ImageEnhance.Brightness(image).enhance(1.08)
    if cache_path is not None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(cache_path, format="PNG")
        except Exception:
            pass
    return image


def _process_openweather_tile_for_panel(tile: Any) -> Any:
    from PIL import Image

    processed = Image.new("RGBA", tile.size, (0, 0, 0, 0))
    source = tile.load()
    target = processed.load()
    width, height = tile.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = source[x, y]
            if a < 12:
                continue
            strength = max(r, g, b)
            if strength < 72:
                colour = (58, 79, 66, min(130, a))
            elif strength < 120:
                colour = (71, 139, 83, min(175, max(a, 120)))
            elif strength < 172:
                colour = (204, 174, 62, min(205, max(a, 150)))
            elif strength < 222:
                colour = (164, 63, 55, min(225, max(a, 170)))
            else:
                colour = (60, 45, 44, min(235, max(a, 190)))
            target[x, y] = colour
    return processed


def _weather_provider_name(provider_id: str) -> str:
    if provider_id == PROVIDER_WEATHER_TODAY_TOMORROW:
        return "Today / Tomorrow Weather"
    if provider_id == PROVIDER_WEATHER_7_DAY:
        return "7-Day Weather Forecast"
    if provider_id == PROVIDER_WEATHER_RADAR:
        return "Weather Radar"
    if provider_id == PROVIDER_WEATHER_PRECIPITATION:
        return "Precipitation Forecast"
    if provider_id == PROVIDER_WEATHER_UV:
        return "UV Forecast"
    if provider_id == PROVIDER_WEATHER_WIND:
        return "Wind Forecast"
    return "Current Weather"


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_slot_pool(value: Any) -> list[int]:
    return parse_slot_pool(value)
