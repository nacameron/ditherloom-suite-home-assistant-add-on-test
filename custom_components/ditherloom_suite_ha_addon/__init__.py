from __future__ import annotations

import asyncio
import base64
import inspect
import json
import shutil
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_CONTENT_ID,
    ATTR_CRC32,
    ATTR_LAST_ERROR,
    ATTR_PAYLOAD_URL,
    ATTR_PREVIEW_URL,
    CONF_DISPLAY_MODE,
    CONF_DISPLAY_ROTATION_ENABLED,
    CONF_DISPLAY_ROTATION_HOURS,
    CONF_DISPLAY_ROTATION_MINUTES,
    CONF_FRAME_HA_ROTATION_ENABLED,
    CONF_FRAME_HA_ROTATION_SECONDS,
    CONF_FRAME_HA_SLOT_CSV,
    CONF_FRAME_HA_SLOT_POOL,
    CONF_FRAME_HOST,
    CONF_FRAME_PORT,
    CONF_FRAME_RESERVED_SLOT,
    CONF_HA_ROTATION_ENABLED,
    CONF_HA_ROTATION_SECONDS,
    CONF_LATITUDE,
    CONF_LOCATION_NAME,
    CONF_LONGITUDE,
    CONF_MAX_JOBS_PER_WAKE,
    CONF_MOON_ENABLED,
    CONF_SUN_ENABLED,
    CONF_TARGET_SLOT,
    CONF_TEMPERATURE_UNIT,
    CONF_TOPIC_BASE,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_WEATHER_LOCATION,
    CONF_WAKE_WINDOW_MINUTES,
    CONF_WAKE_WINDOW_SECONDS,
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
    DEFAULT_HA_ROTATION_SECONDS,
    DEVICE_PACKED_PAYLOAD_BYTES,
    DEVICE_SLOT_COUNT,
    DEVICE_WIFI_B64WRITE_CHUNK_BYTES,
    DEVICE_WIFI_COMMAND_MAX_CHARS,
    DOMAIN,
    MAX_HA_LANE_SLOTS,
    SERVICE_RENDER_MOON,
    SERVICE_RENDER_SUN,
    SERVICE_RENDER_WEATHER,
    SERVICE_SEND_MOON,
    SERVICE_SEND_SUN,
    SERVICE_SEND_WEATHER,
)
from .ha_lane import enabled_content_providers, ha_lane_slots, parse_slot_pool, provider_slot_map, slot_csv, validate_ha_lane

PLATFORMS = ["sensor", "update", "button", "image"]
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.payloads"
DISCOVERY_AUTH_MESSAGE = "Provide a Home Assistant Long-Lived Access Token."
STALE_FRONTEND_ENTITY_NAMES = {
    "Synchronise Wi-Fi " + "wake window",
    "Send weather " + "to frame",
    "Frame schedule " + "status",
}
STALE_FRONTEND_ENTITY_UNIQUE_ID_SUFFIXES = {
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

    hass.http.register_view(DitherloomPayloadView(coordinator))
    hass.http.register_view(DitherloomPreviewView(coordinator))
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

    hass.services.async_register(DOMAIN, SERVICE_RENDER_WEATHER, handle_render_weather)
    hass.services.async_register(DOMAIN, SERVICE_SEND_WEATHER, handle_send_weather)
    hass.services.async_register(DOMAIN, SERVICE_RENDER_SUN, handle_render_sun)
    hass.services.async_register(DOMAIN, SERVICE_SEND_SUN, handle_send_sun)
    hass.services.async_register(DOMAIN, SERVICE_RENDER_MOON, handle_render_moon)
    hass.services.async_register(DOMAIN, SERVICE_SEND_MOON, handle_send_moon)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _async_remove_stale_frontend_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    registry = er.async_get(hass)
    expected_unique_ids = {
        f"{entry.entry_id}_{suffix}" for suffix in STALE_FRONTEND_ENTITY_UNIQUE_ID_SUFFIXES
    }
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity_entry.domain != "button":
            continue
        if entity_entry.unique_id in expected_unique_ids:
            registry.async_remove(entity_entry.entity_id)
            continue
        if entity_entry.original_name in STALE_FRONTEND_ENTITY_NAMES or entity_entry.name in STALE_FRONTEND_ENTITY_NAMES:
            registry.async_remove(entity_entry.entity_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator:
        coordinator.async_cancel_weather_refresh()
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
        if not self.payload_path().exists() or ATTR_CRC32 not in self.last_metadata:
            await self.async_refresh_content_payload(reason="startup")
        else:
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
        else:
            await self.async_publish_job(self.last_metadata)
            self.last_status = "published"
            await self.async_save()
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
        await self.async_refresh_content_payload(reason="frame_awake")

        now = datetime.now(timezone.utc)
        host = str(data.get("ip") or data.get("host") or remote_addr or self.options.get(CONF_FRAME_HOST) or "").strip()
        port = _positive_int(data.get("port")) or int(self.options.get(CONF_FRAME_PORT, DEFAULT_FRAME_PORT))
        target_slot = self._selected_display_slot()
        if not host:
            raise ValueError("Frame awake callback did not include a usable host address")
        if target_slot < 1 or target_slot > DEVICE_SLOT_COUNT:
            raise ValueError(f"Frame target slot {target_slot} is outside the supported slot range")

        await self.async_publish_job(self.last_metadata)
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
        await self.async_save()

        self.hass.async_create_task(self.async_deliver_cached_content_to_announced_frame(host, port, target_slot))
        return {
            "accepted": True,
            "mode": "gateway_push",
            "has_jobs": True,
            "job_count": len(self._enabled_content_providers()),
            "payload_url": self.last_metadata.get(ATTR_PAYLOAD_URL),
            "preview_url": self.last_metadata.get(ATTR_PREVIEW_URL),
            "crc32": self.last_metadata.get(ATTR_CRC32),
            "length": self.last_metadata.get("packed_length"),
            "slot": target_slot,
            "display": True,
        }

    async def async_deliver_cached_content_to_announced_frame(self, host: str, port: int, target_slot: int) -> None:
        try:
            jobs = await self._frame_sync_jobs()
            display_slot = self._selected_display_slot()
            ha_rotation = self._ha_rotation_config()
            gateway_status = await self.hass.async_add_executor_job(_send_gateway_batch_jobs, host, port, jobs, display_slot, ha_rotation)
            synced_at = datetime.now(timezone.utc).isoformat()
            for job in jobs:
                await self._mark_provider_frame_synced(str(job["provider_id"]), str(job["crc32"]), synced_at)
            self.last_status = "frame_awake_sent"
            self.last_metadata["frame_awake_last_success_at"] = synced_at
            self.last_metadata["frame_awake_last_send_host"] = host
            self.last_metadata["frame_awake_last_send_port"] = port
            self.last_metadata["frame_awake_last_target_slot"] = display_slot
            self.last_metadata["frame_awake_last_synced_providers"] = [job["provider_id"] for job in jobs]
            if gateway_status.get("ha_rotation"):
                self.last_metadata["ha_rotation"] = gateway_status["ha_rotation"]
            self.last_metadata.pop(ATTR_LAST_ERROR, None)
        except Exception as exc:
            self.last_status = "frame_awake_send_failed"
            self.last_metadata[ATTR_LAST_ERROR] = f"Frame awake delivery failed: {type(exc).__name__}: {exc}"
            self.last_metadata["frame_awake_last_failed_at"] = datetime.now(timezone.utc).isoformat()
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
        self.last_metadata["frame_sleeping_last_received_at"] = now.isoformat()
        await self.async_save()
        return {"accepted": True, "message": "sleep recorded"}

    async def async_refresh_weather_payload(self, reason: str = "timer") -> dict[str, Any]:
        return await self.async_refresh_content_payload(reason)

    async def async_refresh_content_payload(self, reason: str = "timer") -> dict[str, Any]:
        refreshed: list[str] = []
        for provider in self._enabled_content_providers():
            metadata = await self._read_cached_metadata(provider)
            if metadata is None or not self._cached_content_is_fresh(provider, metadata):
                await self.async_render_provider_to_cache(provider)
                refreshed.append(provider)
        selected = self._selected_content_provider()
        metadata = await self.async_activate_cached_content(selected, reason=reason)
        if metadata is None:
            metadata = await self.async_render_provider_to_cache(selected)
            await self.async_activate_cached_content(selected, reason=reason)
        provider_id = str((metadata or {}).get("provider_id") or selected)
        self.last_status = f"{provider_id}_ready"
        self.last_metadata["content_refresh_reason"] = reason
        self.last_metadata["content_refreshed_providers"] = refreshed
        self.last_metadata["content_refresh_last_success_at"] = datetime.now(timezone.utc).isoformat()
        self.last_metadata["content_refresh_interval_minutes"] = self._effective_update_interval_minutes()
        self.last_metadata["weather_refresh_reason"] = reason
        self.last_metadata["weather_refresh_last_success_at"] = self.last_metadata["content_refresh_last_success_at"]
        self.last_metadata["weather_refresh_interval_minutes"] = self.last_metadata["content_refresh_interval_minutes"]
        self.last_metadata.pop(ATTR_LAST_ERROR, None)
        self._schedule_weather_refresh()
        await self.async_save()
        return metadata

    async def async_render_provider_to_cache(self, provider: str) -> dict[str, Any]:
        if provider == "sunrise_sunset":
            metadata = await self.async_render_sun({}, publish=False, send_to_frame=False, cache_provider_id=provider)
        elif provider == "moon_phase":
            metadata = await self.async_render_moon({}, publish=False, send_to_frame=False, cache_provider_id=provider)
        else:
            metadata = await self.async_render_weather({}, publish=False, send_to_frame=False, cache_provider_id=provider)
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
        else:
            metadata = await self.async_render_weather({}, publish=True, send_to_frame=False, cache_provider_id=provider)
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
        metadata[ATTR_PAYLOAD_URL] = self.payload_url
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["selected_provider_id"] = provider
        metadata["display_rotation_enabled"] = self._display_rotation_enabled()
        metadata["display_rotation_interval_minutes"] = self._display_rotation_interval_minutes()
        metadata["selected_provider_reason"] = reason
        metadata["selected_provider_cache"] = "cached"
        metadata["activated_at"] = datetime.now(timezone.utc).isoformat()
        self.last_status = "published"
        self.last_metadata = metadata
        await self.async_publish_job(metadata)
        await self.async_save()
        return metadata

    async def async_render_weather(
        self,
        data: dict[str, Any],
        publish: bool,
        send_to_frame: bool,
        cache_provider_id: str | None = None,
    ) -> dict[str, Any]:
        from .open_meteo import fetch_open_meteo_card
        from .renderer import render_modern_weather_card, render_to_artifact
        from .renderer.pack import write_artifact

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
        card_data = await self.hass.async_add_executor_job(
            fetch_open_meteo_card,
            latitude,
            longitude,
            location,
            temperature_unit,
            wind_speed_unit,
        )
        display_mode = str(data.get(CONF_DISPLAY_MODE) or opts.get(CONF_DISPLAY_MODE, DEFAULT_DISPLAY_MODE))
        image = render_modern_weather_card(card_data, colour_mode=display_mode)
        artifact = render_to_artifact(image, "weather_current", [card_data.source_entity_id])
        stem = self._provider_payload_name(cache_provider_id) if cache_provider_id else self.latest_payload_name
        await self.hass.async_add_executor_job(write_artifact, artifact, self.payload_dir, stem)
        if cache_provider_id:
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.ppbin", self.payload_path())
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.preview.png", self.preview_path())

        metadata = dict(artifact.metadata)
        metadata[ATTR_PAYLOAD_URL] = self.payload_url
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["update_interval_minutes"] = self._effective_update_interval_minutes()
        metadata["wake_window_seconds"] = self._effective_wake_window_seconds()
        metadata["wake_window_minutes"] = self._effective_wake_window_minutes()
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)
        metadata["display_mode"] = display_mode
        metadata["temperature_unit"] = temperature_unit
        metadata["wind_speed_unit"] = wind_speed_unit
        metadata["provider_id"] = "open_meteo_weather"
        metadata["provider_name"] = "Open-Meteo Weather"
        metadata["source"] = "https://open-meteo.com/"
        metadata["attribution"] = card_data.attribution or "Weather data by Open-Meteo.com."
        for preserved_key in (
            "frame_awake",
            "frame_sleeping",
            "frame_awake_last_received_at",
            "frame_awake_last_success_at",
            "frame_sleeping_last_received_at",
        ):
            preserved = self.last_metadata.get(preserved_key)
            if preserved:
                metadata[preserved_key] = preserved

        self.last_status = "rendered"
        self.last_metadata = metadata

        if publish:
            await self.async_publish_job(metadata)
            self.last_status = "published"
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
        from .renderer import SunCardData, render_sun_card, render_to_artifact
        from .renderer.pack import write_artifact
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

        provider_data = build_sun_provider_data(latitude, longitude, location, self.hass.config.time_zone)
        card_data = SunCardData(**provider_data.__dict__)
        image = render_sun_card(card_data)
        artifact = render_to_artifact(image, "sunrise_sunset", [card_data.source_entity_id])
        stem = self._provider_payload_name(cache_provider_id) if cache_provider_id else self.latest_payload_name
        await self.hass.async_add_executor_job(write_artifact, artifact, self.payload_dir, stem)
        if cache_provider_id:
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.ppbin", self.payload_path())
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.preview.png", self.preview_path())

        metadata = dict(artifact.metadata)
        metadata[ATTR_PAYLOAD_URL] = self.payload_url
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["provider_id"] = "sunrise_sunset"
        metadata["provider_name"] = "Sunrise / Sunset"
        metadata["source"] = "local_solar_calculation"
        metadata["attribution"] = card_data.attribution
        metadata["location"] = card_data.location
        metadata["date_label"] = card_data.date_label
        metadata["sunrise"] = card_data.sunrise
        metadata["sunset"] = card_data.sunset
        metadata["civil_dawn"] = card_data.civil_dawn
        metadata["civil_dusk"] = card_data.civil_dusk
        metadata["day_length"] = card_data.day_length
        metadata["golden_morning"] = card_data.golden_morning
        metadata["golden_evening"] = card_data.golden_evening
        metadata["update_interval_minutes"] = self._effective_update_interval_minutes()
        metadata["wake_window_seconds"] = self._effective_wake_window_seconds()
        metadata["wake_window_minutes"] = self._effective_wake_window_minutes()
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)
        for preserved_key in (
            "frame_awake",
            "frame_sleeping",
            "frame_awake_last_received_at",
            "frame_awake_last_success_at",
            "frame_sleeping_last_received_at",
        ):
            preserved = self.last_metadata.get(preserved_key)
            if preserved:
                metadata[preserved_key] = preserved

        self.last_status = "rendered"
        self.last_metadata = metadata

        if publish:
            await self.async_publish_job(metadata)
            self.last_status = "published"
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
        from .renderer import MoonCardData, render_moon_card, render_to_artifact
        from .renderer.pack import write_artifact

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

        provider_data = build_moon_provider_data(latitude, longitude, location, self.hass.config.time_zone)
        card_data = MoonCardData(**provider_data.__dict__)
        image = render_moon_card(card_data)
        artifact = render_to_artifact(image, "moon_phase", [card_data.source_entity_id])
        stem = self._provider_payload_name(cache_provider_id) if cache_provider_id else self.latest_payload_name
        await self.hass.async_add_executor_job(write_artifact, artifact, self.payload_dir, stem)
        if cache_provider_id:
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.ppbin", self.payload_path())
            await self.hass.async_add_executor_job(shutil.copyfile, self.payload_dir / f"{stem}.preview.png", self.preview_path())

        metadata = dict(artifact.metadata)
        metadata[ATTR_PAYLOAD_URL] = self.payload_url
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["provider_id"] = "moon_phase"
        metadata["provider_name"] = "Moon Phase"
        metadata["source"] = "local_moon_calculation"
        metadata["attribution"] = card_data.attribution
        metadata["location"] = card_data.location
        metadata["date_label"] = card_data.date_label
        metadata["phase_name"] = card_data.phase_name
        metadata["illumination"] = card_data.illumination
        metadata["moon_age"] = card_data.moon_age
        metadata["moonrise"] = card_data.moonrise
        metadata["moonset"] = card_data.moonset
        metadata["next_full"] = card_data.next_full
        metadata["next_new"] = card_data.next_new
        metadata["update_interval_minutes"] = self._effective_update_interval_minutes()
        metadata["wake_window_seconds"] = self._effective_wake_window_seconds()
        metadata["wake_window_minutes"] = self._effective_wake_window_minutes()
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)
        for preserved_key in (
            "frame_awake",
            "frame_sleeping",
            "frame_awake_last_received_at",
            "frame_awake_last_success_at",
            "frame_sleeping_last_received_at",
        ):
            preserved = self.last_metadata.get(preserved_key)
            if preserved:
                metadata[preserved_key] = preserved

        self.last_status = "rendered"
        self.last_metadata = metadata

        if publish:
            await self.async_publish_job(metadata)
            self.last_status = "published"
        if send_to_frame:
            await self.async_send_to_frame(artifact.packed, artifact.crc32)
            self.last_status = "sent"
            self.last_metadata.pop(ATTR_LAST_ERROR, None)

        await self.async_save()
        return metadata

    def _effective_update_interval_minutes(self) -> int:
        return _positive_int(self.options.get(CONF_UPDATE_INTERVAL_MINUTES)) or DEFAULT_UPDATE_INTERVAL_MINUTES

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

    def _ha_owned_slots(self) -> list[int]:
        return ha_lane_slots(self.options)

    def _ha_slot_csv(self) -> str:
        return slot_csv(self._ha_owned_slots())

    def _reserved_ha_slot(self) -> int:
        slots = self._ha_owned_slots()
        return slots[0] if slots else int(self.options.get(CONF_TARGET_SLOT, DEFAULT_TARGET_SLOT))

    def _ha_slot_pool_text(self) -> str:
        options = self.options
        if options.get(CONF_FRAME_HA_SLOT_POOL):
            return str(options.get(CONF_FRAME_HA_SLOT_POOL))
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
        return {"enabled": self._ha_rotation_enabled(), "seconds": self._ha_rotation_seconds(), "slots": self._ha_owned_slots()}

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
        if provider == "open_meteo_weather":
            return "content-weather"
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
        if provider in {"sunrise_sunset", "moon_phase"}:
            return metadata.get("date_label") == datetime.now(self._local_timezone()).strftime("%d %b").upper()
        rendered_at = _parse_datetime(metadata.get("rendered_at"))
        if rendered_at is None:
            return False
        age = datetime.now(timezone.utc) - rendered_at.astimezone(timezone.utc)
        return age < timedelta(minutes=self._effective_update_interval_minutes())

    def _local_timezone(self):
        from zoneinfo import ZoneInfo

        try:
            return ZoneInfo(self.hass.config.time_zone or "UTC")
        except Exception:
            return timezone.utc

    async def _frame_sync_jobs(self) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        slot_map = self._provider_slot_map()
        for provider in self._enabled_content_providers():
            metadata = await self._read_cached_metadata(provider)
            if metadata is None or not self._cached_content_is_fresh(provider, metadata):
                metadata = await self.async_render_provider_to_cache(provider)
            if not self._provider_needs_frame_sync(provider, metadata):
                continue
            stem = self._provider_payload_name(provider)
            packed = await self.hass.async_add_executor_job((self.payload_dir / f"{stem}.ppbin").read_bytes)
            jobs.append(
                {
                    "provider_id": provider,
                    "slot": slot_map[provider],
                    "packed": packed,
                    "crc32": str(metadata[ATTR_CRC32]),
                    "content_id": metadata.get(ATTR_CONTENT_ID),
                    "date_label": metadata.get("date_label"),
                }
            )
        self.last_metadata["ha_owned_slots"] = slot_map
        return jobs

    def _provider_needs_frame_sync(self, provider: str, metadata: dict[str, Any]) -> bool:
        if metadata.get("frame_synced_crc32") != metadata.get(ATTR_CRC32):
            return True
        if provider in {"sunrise_sunset", "moon_phase"}:
            today = datetime.now(self._local_timezone()).strftime("%d %b").upper()
            return metadata.get("frame_synced_date_label") != today
        synced_at = _parse_datetime(metadata.get("frame_synced_at"))
        if synced_at is None:
            return True
        age = datetime.now(timezone.utc) - synced_at.astimezone(timezone.utc)
        return age >= timedelta(minutes=self._effective_update_interval_minutes())

    async def _mark_provider_frame_synced(self, provider: str, crc32: str, synced_at: str) -> None:
        metadata = await self._read_cached_metadata(provider)
        if metadata is None:
            return
        metadata["frame_synced_at"] = synced_at
        metadata["frame_synced_crc32"] = crc32
        metadata["frame_synced_date_label"] = metadata.get("date_label") or datetime.now(self._local_timezone()).strftime("%d %b").upper()
        await self._write_cached_metadata(provider, metadata)

    def async_cancel_weather_refresh(self) -> None:
        if self._weather_refresh_unsub:
            self._weather_refresh_unsub()
            self._weather_refresh_unsub = None

    def _schedule_weather_refresh(self) -> None:
        interval_minutes = self._effective_update_interval_minutes()
        interval = timedelta(minutes=interval_minutes)
        self.async_cancel_weather_refresh()
        self.last_metadata["weather_refresh_interval_minutes"] = interval_minutes
        self.last_metadata["weather_refresh_next_at"] = (datetime.now(timezone.utc) + interval).isoformat()
        self._weather_refresh_unsub = async_track_time_interval(self.hass, self._handle_weather_refresh, interval)

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
    def payload_url(self) -> str:
        return f"/api/ditherloom/{self.entry.entry_id}/payload/{self.latest_payload_name}.ppbin"

    @property
    def preview_url(self) -> str:
        return f"/api/ditherloom/{self.entry.entry_id}/preview/{self.latest_payload_name}.preview.png"

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
            "reservedSlot": self._reserved_ha_slot(),
            "haSlotPool": self._ha_slot_pool_text(),
            "haSlotCsv": self._ha_slot_csv(),
            "haRotationEnabled": self._ha_rotation_enabled(),
            "haRotationSeconds": self._ha_rotation_seconds(),
            "haRotationStatus": self.last_metadata.get("ha_rotation"),
            "payloadPath": self.payload_url,
            "payloadUrl": f"{origin}{self.payload_url}",
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
                "intervalMinutes": self._effective_update_interval_minutes(),
                "wakeWindowSeconds": self._effective_wake_window_seconds(),
                "maxJobsPerWake": options.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE),
                "reservedSlot": self._reserved_ha_slot(),
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

    async def async_publish_job(self, metadata: dict[str, Any]) -> None:
        topic_base = self.options.get(CONF_TOPIC_BASE) or f"ditherloom/{self.entry.data.get('library_id')}"
        now = datetime.now(timezone.utc)
        wake_window_seconds = self._effective_wake_window_seconds()
        provider_id = str(metadata.get("provider_id") or metadata.get("selected_provider_id") or "open_meteo_weather")
        slot = self._provider_slot_map().get(provider_id, self._reserved_ha_slot())
        job = {
            "command_id": f"ha-{metadata.get('provider_id', 'weather')}-{now.strftime('%Y%m%d-%H%M%S')}-{metadata[ATTR_CRC32].lower()}",
            "job_type": "content_card",
            "content_id": metadata[ATTR_CONTENT_ID],
            "source": "home_assistant",
            "template": metadata.get("template_name", "weather_current"),
            "slot": slot,
            "ha_owned_slots": self._provider_slot_map(),
            "display": True,
            "payload_url": metadata[ATTR_PAYLOAD_URL],
            "length": metadata["packed_length"],
            "crc32": metadata[ATTR_CRC32],
            "expires_at": (now + timedelta(seconds=wake_window_seconds)).isoformat(),
            "fallback_slot": "random",
            "sleep_policy": "sleep_after_completion",
            "wake_window_seconds": wake_window_seconds,
            "wake_window_minutes": self._effective_wake_window_minutes(),
            "max_jobs_per_wake": self.options.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE),
        }
        if self.hass.services.has_service("mqtt", "publish"):
            await self.hass.services.async_call(
                "mqtt",
                "publish",
                {
                    "topic": f"{topic_base}/cmd/job",
                    "payload": json.dumps(job),
                    "qos": 1,
                    "retain": False,
                },
                blocking=True,
            )
        self.last_metadata["last_job"] = job

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
    manifest_path = Path(__file__).with_name("manifest.json")
    try:
        return str(json.loads(manifest_path.read_text(encoding="utf-8")).get("version") or "")
    except Exception:
        return ""


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


class DitherloomPayloadView(HomeAssistantView):
    requires_auth = False

    def __init__(self, runtime: DitherloomRuntime) -> None:
        self.runtime = runtime
        self.url = f"/api/ditherloom/{runtime.entry.entry_id}/payload/{{filename}}"
        self.name = f"api:{DOMAIN}:payload:{runtime.entry.entry_id}"

    async def get(self, request, filename: str):
        path = self.runtime.payload_path()
        if filename != path.name or not path.exists():
            return self.json({"error": "not_found"}, status_code=404)
        return web.FileResponse(
            path,
            headers={
                "Content-Type": "application/octet-stream",
                "Cache-Control": "no-store",
            },
        )


async def _store_frame_provided_ha_config(hass: HomeAssistant, entry: ConfigEntry, body: dict[str, Any]) -> None:
    updates: dict[str, Any] = {}
    if "reservedSlot" in body:
        reserved = _positive_int(body.get("reservedSlot"))
        if reserved is not None:
            updates[CONF_FRAME_RESERVED_SLOT] = reserved
    if "haSlotPool" in body:
        updates[CONF_FRAME_HA_SLOT_POOL] = str(body.get("haSlotPool") or "").strip()
    if "haSlotCsv" in body:
        updates[CONF_FRAME_HA_SLOT_CSV] = slot_csv(parse_slot_pool(body.get("haSlotCsv")))
    elif updates.get(CONF_FRAME_RESERVED_SLOT) is not None:
        slots = [updates[CONF_FRAME_RESERVED_SLOT]]
        for slot in parse_slot_pool(updates.get(CONF_FRAME_HA_SLOT_POOL, "")):
            if slot not in slots:
                slots.append(slot)
        updates[CONF_FRAME_HA_SLOT_CSV] = slot_csv(slots)
    if "haRotationEnabled" in body:
        updates[CONF_FRAME_HA_ROTATION_ENABLED] = bool(body.get("haRotationEnabled"))
    if "haRotationSeconds" in body:
        seconds = _positive_int(body.get("haRotationSeconds"))
        if seconds is not None:
            updates[CONF_FRAME_HA_ROTATION_SECONDS] = max(60, seconds)
    if not updates:
        return
    options = {**entry.options, **updates}
    hass.config_entries.async_update_entry(entry, options=options)


def _frame_provided_ha_config(options: dict[str, Any]) -> dict[str, Any]:
    slots = ha_lane_slots(options)
    return {
        "reservedSlot": slots[0] if slots else None,
        "haSlotPool": str(options.get(CONF_FRAME_HA_SLOT_POOL) or slot_csv(slots[1:])),
        "haSlotCsv": slot_csv(slots),
        "haRotationEnabled": _bool_option(options, CONF_FRAME_HA_ROTATION_ENABLED, False),
        "haRotationSeconds": _positive_int(options.get(CONF_FRAME_HA_ROTATION_SECONDS)) or DEFAULT_HA_ROTATION_SECONDS,
    }


class DitherloomPreviewView(HomeAssistantView):
    requires_auth = False

    def __init__(self, runtime: DitherloomRuntime) -> None:
        self.runtime = runtime
        self.url = f"/api/ditherloom/{runtime.entry.entry_id}/preview/{{filename}}"
        self.name = f"api:{DOMAIN}:preview:{runtime.entry.entry_id}"

    async def get(self, request, filename: str):
        path = self.runtime.preview_path()
        if filename != path.name or not path.exists():
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
    ha_rotation_slots = [int(slot) for slot in (ha_rotation or {}).get("slots", [])]
    if len(ha_rotation_slots) > MAX_HA_LANE_SLOTS:
        raise ValueError(f"HA rotation supports up to {MAX_HA_LANE_SLOTS} HA-owned slots")
    for slot in ha_rotation_slots:
        if slot < 1 or slot > DEVICE_SLOT_COUNT:
            raise ValueError(f"HA rotation slot must be between 1 and {DEVICE_SLOT_COUNT}, got {slot}")
    if ha_rotation_enabled:
        job_slots = {int(job["slot"]) for job in jobs}
        missing_slots = [slot for slot in ha_rotation_slots if slot not in job_slots]
        if missing_slots:
            raise ValueError(f"HA rotation slots have no uploaded provider payload: {slot_csv(missing_slots)}")
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
                _set_gateway_ha_rotation(sock_file, int((ha_rotation or {}).get("seconds") or DEFAULT_HA_ROTATION_SECONDS), ha_rotation_slots)
            if display_slot is not None:
                _ensure_gateway_slot_is_ha(sock_file, display_slot)
                display = _send_gateway_stage(sock_file, f"DISPLAY {display_slot}", "DISPLAY")
                if not display.startswith("OK"):
                    raise RuntimeError(f"DISPLAY failed: {display}")
        except Exception:
            _best_effort_open_connection_idle(sock_file)
            raise
        else:
            _best_effort_open_connection_idle(sock_file)
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
    if len(slots) > MAX_HA_LANE_SLOTS:
        raise RuntimeError(f"HA rotation supports up to {MAX_HA_LANE_SLOTS} HA-owned slots")
    for slot in slots:
        _ensure_gateway_slot_is_ha(sock_file, slot)
    command = f"HAROTATION on {max(60, int(seconds))} {slot_csv(slots)}"
    response = _send_gateway_stage(sock_file, command, "HAROTATION")
    if not _harotation_on_response_ok(response, seconds, slots):
        raise RuntimeError(f"HAROTATION failed or firmware rejected HA rotation slots: {response}")


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


def _bool_option(data: dict[str, Any], key: str, default: bool) -> bool:
    return bool(data[key]) if key in data else default


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
