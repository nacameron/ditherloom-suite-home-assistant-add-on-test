from __future__ import annotations

import asyncio
import base64
import json
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_CONTENT_ID,
    ATTR_CRC32,
    ATTR_LAST_ERROR,
    ATTR_PAYLOAD_URL,
    ATTR_PREVIEW_URL,
    CONF_FRAME_HOST,
    CONF_FRAME_PORT,
    CONF_LATITUDE,
    CONF_LOCATION_NAME,
    CONF_LONGITUDE,
    CONF_MAX_JOBS_PER_WAKE,
    CONF_TARGET_SLOT,
    CONF_TOPIC_BASE,
    CONF_WAKE_WINDOW_MINUTES,
    DEFAULT_FRAME_PORT,
    DEFAULT_MAX_JOBS_PER_WAKE,
    DEFAULT_TARGET_SLOT,
    DEFAULT_WAKE_WINDOW_MINUTES,
    DOMAIN,
    SERVICE_RENDER_WEATHER,
    SERVICE_SEND_WEATHER,
)
from .open_meteo import fetch_open_meteo_card
from .renderer import render_to_artifact, render_weather_card
from .renderer.pack import write_artifact

PLATFORMS = ["sensor"]
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.payloads"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")
    coordinator = DitherloomRuntime(hass, entry, store)
    await coordinator.async_load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    hass.http.register_view(DitherloomPayloadView(coordinator))
    hass.http.register_view(DitherloomPreviewView(coordinator))

    async def handle_render_weather(call: ServiceCall) -> None:
        await coordinator.async_render_weather(dict(call.data), publish=False, send_to_frame=False)

    async def handle_send_weather(call: ServiceCall) -> None:
        await coordinator.async_render_weather(dict(call.data), publish=True, send_to_frame=True)

    hass.services.async_register(DOMAIN, SERVICE_RENDER_WEATHER, handle_render_weather)
    hass.services.async_register(DOMAIN, SERVICE_SEND_WEATHER, handle_send_weather)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


@dataclass
class DitherloomRuntime:
    hass: HomeAssistant
    entry: ConfigEntry
    store: Store
    payload_dir: Path = field(init=False)
    last_status: str = "idle"
    last_metadata: dict[str, Any] = field(default_factory=dict)
    latest_payload_name: str = "weather-current"

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

    async def async_save(self) -> None:
        await self.store.async_save(
            {
                "last_status": self.last_status,
                "last_metadata": self.last_metadata,
            }
        )

    async def async_render_weather(self, data: dict[str, Any], publish: bool, send_to_frame: bool) -> dict[str, Any]:
        opts = self.options
        latitude = str(data.get(CONF_LATITUDE) or opts.get(CONF_LATITUDE) or "0")
        longitude = str(data.get(CONF_LONGITUDE) or opts.get(CONF_LONGITUDE) or "0")
        location = str(data.get(CONF_LOCATION_NAME) or opts.get(CONF_LOCATION_NAME) or "Home")

        card_data = await self.hass.async_add_executor_job(fetch_open_meteo_card, latitude, longitude, location)
        image = render_weather_card(card_data)
        artifact = render_to_artifact(image, "weather_current", [card_data.source_entity_id])
        await self.hass.async_add_executor_job(write_artifact, artifact, self.payload_dir, self.latest_payload_name)

        metadata = dict(artifact.metadata)
        metadata[ATTR_PAYLOAD_URL] = self.payload_url
        metadata[ATTR_PREVIEW_URL] = self.preview_url
        metadata["rendered_at"] = datetime.now(timezone.utc).isoformat()
        metadata["wake_window_minutes"] = opts.get(CONF_WAKE_WINDOW_MINUTES, DEFAULT_WAKE_WINDOW_MINUTES)
        metadata["max_jobs_per_wake"] = opts.get(CONF_MAX_JOBS_PER_WAKE, DEFAULT_MAX_JOBS_PER_WAKE)

        self.last_status = "rendered"
        self.last_metadata = metadata

        if publish:
            await self.async_publish_job(metadata)
            self.last_status = "published"
        if send_to_frame:
            await self.async_send_to_frame(artifact.packed, artifact.crc32)
            self.last_status = "sent"

        await self.async_save()
        return metadata

    @property
    def payload_url(self) -> str:
        return f"/api/ditherloom/{self.entry.entry_id}/payload/{self.latest_payload_name}.ppbin"

    @property
    def preview_url(self) -> str:
        return f"/api/ditherloom/{self.entry.entry_id}/preview/{self.latest_payload_name}.preview.png"

    def payload_path(self) -> Path:
        return self.payload_dir / f"{self.latest_payload_name}.ppbin"

    def preview_path(self) -> Path:
        return self.payload_dir / f"{self.latest_payload_name}.preview.png"

    async def async_publish_job(self, metadata: dict[str, Any]) -> None:
        topic_base = self.options.get(CONF_TOPIC_BASE) or f"ditherloom/{self.entry.data.get('library_id')}"
        now = datetime.now(timezone.utc)
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
            "expires_at": (now + timedelta(minutes=int(self.options.get(CONF_WAKE_WINDOW_MINUTES, 5)))).isoformat(),
            "fallback_slot": "random",
            "sleep_policy": "sleep_after_completion",
            "wake_window_minutes": self.options.get(CONF_WAKE_WINDOW_MINUTES, DEFAULT_WAKE_WINDOW_MINUTES),
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
        await self.hass.async_add_executor_job(_send_existing_gateway_job, host, port, packed, crc32, target_slot)


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
        return web.FileResponse(path, headers={"Content-Type": "application/octet-stream"})


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
        return web.FileResponse(path, headers={"Content-Type": "image/png"})


def _readline(sock_file) -> str:
    line = sock_file.readline()
    if not line:
        raise RuntimeError("Frame closed Gateway connection")
    return line.decode("utf-8", errors="replace").strip()


def _send_command(sock_file, command: str) -> str:
    sock_file.write((command + "\n").encode("utf-8"))
    sock_file.flush()
    return _readline(sock_file)


def _send_existing_gateway_job(host: str, port: int, packed: bytes, crc32: str, slot: int) -> None:
    with socket.create_connection((host, port), timeout=20) as sock:
        sock.settimeout(30)
        sock_file = sock.makefile("rwb")
        pong = _send_command(sock_file, "PING")
        if not pong.startswith("OK"):
            raise RuntimeError(f"PING failed: {pong}")
        begin = _send_command(sock_file, f"BEGIN {slot} {len(packed)} {crc32}")
        if not begin.startswith("OK"):
            raise RuntimeError(f"BEGIN failed: {begin}")
        offset = 0
        chunk_size = 768
        while offset < len(packed):
            chunk = packed[offset : offset + chunk_size]
            encoded = base64.b64encode(chunk).decode("ascii")
            response = _send_command(sock_file, f"B64WRITE {slot} {offset} {encoded}")
            if not response.startswith("OK"):
                raise RuntimeError(f"B64WRITE failed at {offset}: {response}")
            offset += len(chunk)
        end = _send_command(sock_file, f"END {slot}")
        if not end.startswith("OK"):
            raise RuntimeError(f"END failed: {end}")
        display = _send_command(sock_file, f"DISPLAY {slot}")
        if not display.startswith("OK"):
            raise RuntimeError(f"DISPLAY failed: {display}")
        _send_command(sock_file, "IDLE")
