from __future__ import annotations

import asyncio
import base64
import json
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
    CONF_FRAME_HOST,
    CONF_FRAME_PORT,
    CONF_LATITUDE,
    CONF_LOCATION_NAME,
    CONF_LONGITUDE,
    CONF_MAX_JOBS_PER_WAKE,
    CONF_TARGET_SLOT,
    CONF_TEMPERATURE_UNIT,
    CONF_TOPIC_BASE,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_WEATHER_LOCATION,
    CONF_WAKE_WINDOW_MINUTES,
    CONF_WAKE_WINDOW_SECONDS,
    CONF_WIND_SPEED_UNIT,
    DEFAULT_FRAME_PORT,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_MAX_JOBS_PER_WAKE,
    DEFAULT_TARGET_SLOT,
    DEFAULT_TEMPERATURE_UNIT,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DEFAULT_WAKE_WINDOW_MINUTES,
    DEFAULT_WIND_SPEED_UNIT,
    DEVICE_PACKED_PAYLOAD_BYTES,
    DEVICE_SLOT_COUNT,
    DEVICE_WIFI_B64WRITE_CHUNK_BYTES,
    DEVICE_WIFI_COMMAND_MAX_CHARS,
    DOMAIN,
    SERVICE_RENDER_WEATHER,
    SERVICE_SEND_WEATHER,
)

PLATFORMS = ["sensor", "update", "button", "image"]
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.payloads"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.http.register_view(DitherloomDiscoveryView(hass))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")
    coordinator = DitherloomRuntime(hass, entry, store)
    await coordinator.async_load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_start()

    hass.http.register_view(DitherloomPayloadView(coordinator))
    hass.http.register_view(DitherloomPreviewView(coordinator))
    hass.http.register_view(DitherloomFrameAwakeView(coordinator))
    hass.http.register_view(DitherloomFrameSleepingView(coordinator))

    async def handle_render_weather(call: ServiceCall) -> None:
        await _handle_weather_service(coordinator, call, publish=False, send_to_frame=False, action="render weather")

    async def handle_send_weather(call: ServiceCall) -> None:
        await _handle_weather_service(coordinator, call, publish=True, send_to_frame=True, action="send weather")

    hass.services.async_register(DOMAIN, SERVICE_RENDER_WEATHER, handle_render_weather)
    hass.services.async_register(DOMAIN, SERVICE_SEND_WEATHER, handle_send_weather)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


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
            await self.async_refresh_weather_payload(reason="startup")
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
            await self.async_render_weather({}, publish=True, send_to_frame=False)
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
        if not self.payload_path().exists() or ATTR_CRC32 not in self.last_metadata:
            await self.async_refresh_weather_payload(reason="frame_awake_missing_payload")

        now = datetime.now(timezone.utc)
        host = str(data.get("ip") or data.get("host") or remote_addr or self.options.get(CONF_FRAME_HOST) or "").strip()
        port = _positive_int(data.get("port")) or int(self.options.get(CONF_FRAME_PORT, DEFAULT_FRAME_PORT))
        target_slot = _positive_int(data.get("reservedSlot") or data.get("reserved_slot")) or int(
            self.options.get(CONF_TARGET_SLOT, DEFAULT_TARGET_SLOT)
        )
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
        }
        self.last_metadata["frame_awake_last_received_at"] = now.isoformat()
        await self.async_save()

        self.hass.async_create_task(self.async_deliver_cached_weather_to_announced_frame(host, port, target_slot))
        return {
            "accepted": True,
            "mode": "gateway_push",
            "has_jobs": True,
            "job_count": 1,
            "payload_url": self.last_metadata.get(ATTR_PAYLOAD_URL),
            "preview_url": self.last_metadata.get(ATTR_PREVIEW_URL),
            "crc32": self.last_metadata.get(ATTR_CRC32),
            "length": self.last_metadata.get("packed_length"),
            "slot": target_slot,
            "display": True,
        }

    async def async_deliver_cached_weather_to_announced_frame(self, host: str, port: int, target_slot: int) -> None:
        try:
            packed = await self.hass.async_add_executor_job(self.payload_path().read_bytes)
            crc32 = str(self.last_metadata[ATTR_CRC32])
            await self.async_send_to_frame_host(host, port, packed, crc32, target_slot)
            self.last_status = "frame_awake_sent"
            self.last_metadata["frame_awake_last_success_at"] = datetime.now(timezone.utc).isoformat()
            self.last_metadata["frame_awake_last_send_host"] = host
            self.last_metadata["frame_awake_last_send_port"] = port
            self.last_metadata["frame_awake_last_target_slot"] = target_slot
            self.last_metadata.pop(ATTR_LAST_ERROR, None)
        except Exception as exc:
            self.last_status = "frame_awake_send_failed"
            self.last_metadata[ATTR_LAST_ERROR] = f"Frame awake delivery failed: {type(exc).__name__}: {exc}"
            self.last_metadata["frame_awake_last_failed_at"] = datetime.now(timezone.utc).isoformat()
            self._create_notification("Ditherloom frame awake delivery failed", str(self.last_metadata[ATTR_LAST_ERROR]))
        finally:
            await self.async_save()

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
        metadata = await self.async_render_weather({}, publish=True, send_to_frame=False)
        self.last_status = "weather_ready"
        self.last_metadata["weather_refresh_reason"] = reason
        self.last_metadata["weather_refresh_last_success_at"] = datetime.now(timezone.utc).isoformat()
        self.last_metadata["weather_refresh_interval_minutes"] = self._effective_update_interval_minutes()
        self.last_metadata.pop(ATTR_LAST_ERROR, None)
        self._schedule_weather_refresh()
        await self.async_save()
        return metadata

    async def async_render_weather(self, data: dict[str, Any], publish: bool, send_to_frame: bool) -> dict[str, Any]:
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
        await self.hass.async_add_executor_job(write_artifact, artifact, self.payload_dir, self.latest_payload_name)

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
            self.last_status = "weather_refresh_failed"
            self.last_metadata[ATTR_LAST_ERROR] = f"Weather refresh failed: {type(exc).__name__}: {exc}"
            self.last_metadata["weather_refresh_last_failed_at"] = now.isoformat()
            self._create_notification("Ditherloom weather refresh failed", str(self.last_metadata[ATTR_LAST_ERROR]))
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
        return {
            "integrationInstalled": True,
            "integrationDomain": DOMAIN,
            "integrationName": "Ditherloom Suite Home Assistant Add On",
            "entryId": self.entry.entry_id,
            "libraryId": self.entry.data.get("library_id"),
            "haUrl": origin,
            "callbackBasePath": callback_base_path,
            "frameAwakePath": self.frame_awake_url,
            "frameSleepingPath": self.frame_sleeping_url,
            "frameAwakeUrl": f"{origin}{self.frame_awake_url}",
            "frameSleepingUrl": f"{origin}{self.frame_sleeping_url}",
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
                "reservedSlot": options.get(CONF_TARGET_SLOT, DEFAULT_TARGET_SLOT),
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
        job = {
            "command_id": f"ha-weather-{now.strftime('%Y%m%d-%H%M%S')}-{metadata[ATTR_CRC32].lower()}",
            "job_type": "content_card",
            "content_id": metadata[ATTR_CONTENT_ID],
            "source": "home_assistant",
            "template": "weather_current",
            "slot": int(self.options.get(CONF_TARGET_SLOT, DEFAULT_TARGET_SLOT)),
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
        target_slot = int(self.options.get(CONF_TARGET_SLOT, DEFAULT_TARGET_SLOT))
        await self.async_send_to_frame_host(host, port, packed, crc32, target_slot)

    async def async_send_to_frame_host(self, host: str, port: int, packed: bytes, crc32: str, target_slot: int) -> None:
        if not host:
            raise ValueError("Frame host is not configured")
        if target_slot < 1 or target_slot > DEVICE_SLOT_COUNT:
            raise ValueError(f"Frame target slot {target_slot} is outside the supported slot range")
        await self.hass.async_add_executor_job(_send_existing_gateway_job, host, port, packed, crc32, target_slot)


class DitherloomDiscoveryView(HomeAssistantView):
    requires_auth = True
    url = "/api/ditherloom/discovery"
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
                    "integrationInstalled": False,
                    "integrationDomain": DOMAIN,
                    "error": "No configured Ditherloom integration entry matched the request",
                },
                status_code=404,
            )
        if len(runtimes) > 1:
            return self.json(
                {
                    "integrationInstalled": True,
                    "integrationDomain": DOMAIN,
                    "error": "Multiple Ditherloom integration entries are configured; include library_id",
                    "entries": [
                        {
                            "entryId": runtime.entry.entry_id,
                            "libraryId": runtime.entry.data.get("library_id"),
                        }
                        for runtime in runtimes
                    ],
                },
                status_code=409,
            )

        origin = f"{request.scheme}://{request.host}"
        return self.json(runtimes[0].app_discovery_payload(origin))


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
    if len(packed) != DEVICE_PACKED_PAYLOAD_BYTES:
        raise ValueError(f"Packed payload must be exactly {DEVICE_PACKED_PAYLOAD_BYTES} bytes, got {len(packed)}")
    if slot < 1 or slot > DEVICE_SLOT_COUNT:
        raise ValueError(f"Target slot must be between 1 and {DEVICE_SLOT_COUNT}, got {slot}")

    with socket.create_connection((host, port), timeout=20) as sock:
        sock.settimeout(30)
        sock_file = sock.makefile("rwb")
        try:
            pong = _send_gateway_stage(sock_file, "PING", "PING")
            if not pong.startswith("OK"):
                raise RuntimeError(f"PING failed: {pong}")
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
            display = _send_gateway_stage(sock_file, f"DISPLAY {slot}", "DISPLAY")
            if not display.startswith("OK"):
                raise RuntimeError(f"DISPLAY failed: {display}")
        except Exception:
            _best_effort_open_connection_idle(sock_file)
            raise
        else:
            _best_effort_open_connection_idle(sock_file)


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
