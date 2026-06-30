from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

PROVIDER_DISPLAY_NAMES = {
    "open_meteo_weather": "Open-Meteo Weather",
    "sunrise_sunset": "Sunrise / Sunset",
    "moon_phase": "Moon Phase",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DitherloomStatusSensor(coordinator, entry),
            DitherloomFrameScheduleSensor(coordinator, entry),
        ]
    )


class DitherloomSensorBase(SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._remove_listener = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ditherloom Suite Home Assistant Add On",
        )

    async def async_added_to_hass(self) -> None:
        self._remove_listener = self._coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None


class DitherloomStatusSensor(DitherloomSensorBase):
    _attr_name = "Last job status"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_job_status"

    @property
    def native_value(self):
        return self._coordinator.last_status

    @property
    def extra_state_attributes(self):
        return self._coordinator.last_metadata


class DitherloomFrameScheduleSensor(DitherloomSensorBase):
    _attr_name = "Frame handshake status"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_frame_handshake_status"

    @property
    def native_value(self):
        metadata = self._coordinator.last_metadata
        failed_at = _parse_iso_datetime(metadata.get("frame_awake_last_failed_at"))
        delivered_at = _parse_iso_datetime(metadata.get("frame_awake_last_success_at"))
        awake_at = _parse_iso_datetime(metadata.get("frame_awake_last_received_at"))
        sleeping_at = _parse_iso_datetime(metadata.get("frame_sleeping_last_received_at"))
        latest = max((item for item in (failed_at, delivered_at, awake_at, sleeping_at) if item is not None), default=None)
        if failed_at is not None and failed_at == latest:
            return f"delivery failed {_state_time_label(failed_at)}"
        if delivered_at is not None and delivered_at == latest:
            count = _delivered_job_count(metadata)
            return f"delivered {count} job{'s' if count != 1 else ''} {_state_time_label(delivered_at)}"
        if sleeping_at is not None and sleeping_at == latest and delivered_at is not None:
            count = _delivered_job_count(metadata)
            return f"delivered {count} job{'s' if count != 1 else ''} {_state_time_label(delivered_at)}"
        if awake_at is not None and awake_at == latest:
            return f"frame awake {_state_time_label(awake_at)}"
        if metadata.get("content_refresh_last_success_at") or metadata.get("weather_refresh_last_success_at") or metadata.get("rendered_at"):
            rendered_at = _parse_iso_datetime(metadata.get("content_rendered_at") or metadata.get("rendered_at"))
            if rendered_at is not None:
                return f"content ready {_state_time_label(rendered_at)}"
            return "content ready"
        return "waiting for content"

    @property
    def extra_state_attributes(self):
        metadata = self._coordinator.last_metadata
        frame_ha_config = metadata.get("frame_ha_config") or (metadata.get("frame_awake") or {}).get("ha_config") or {}
        frame_awake = metadata.get("frame_awake") or {}
        frame_interval_minutes = frame_ha_config.get("intervalMinutes")
        frame_ha_rotation_seconds = frame_ha_config.get("haRotationSeconds")
        frame_wake_window_seconds = frame_awake.get("wake_window_seconds") or frame_ha_config.get("wakeWindowSeconds")
        delivered_provider_ids = _delivered_provider_ids(metadata)
        delivered_provider_names = [_provider_display_name(provider_id) for provider_id in delivered_provider_ids]
        delivered_summary = _delivered_summary(metadata, delivered_provider_names)
        return {
            "weather_refresh_next_at": metadata.get("weather_refresh_next_at"),
            "weather_refresh_interval_minutes": metadata.get("weather_refresh_interval_minutes"),
            "weather_refresh_last_success_at": metadata.get("weather_refresh_last_success_at"),
            "content_refresh_last_success_at": metadata.get("content_refresh_last_success_at"),
            "content_rendered_at": metadata.get("content_rendered_at") or metadata.get("rendered_at"),
            "content_rendered_provider_id": metadata.get("content_rendered_provider_id") or metadata.get("provider_id"),
            "content_rendered_content_id": metadata.get("content_rendered_content_id") or metadata.get("content_id"),
            "content_rendered_crc32": metadata.get("content_rendered_crc32") or metadata.get("crc32"),
            "frame_content_last_delivered_at": metadata.get("frame_content_last_delivered_at"),
            "frame_content_last_delivered_count": metadata.get("frame_content_last_delivered_count"),
            "frame_content_last_delivered_slots": metadata.get("frame_content_last_delivered_slots"),
            "frame_content_last_delivered_crc32": metadata.get("frame_content_last_delivered_crc32"),
            "frame_content_last_delivered_content_ids": metadata.get("frame_content_last_delivered_content_ids"),
            "frame_content_last_delivered_provider_ids": delivered_provider_ids,
            "frame_content_last_delivered_provider_names": delivered_provider_names,
            "frame_content_last_delivered_summary": delivered_summary,
            "frame_awake_last_delivered_jobs": metadata.get("frame_awake_last_delivered_jobs"),
            "frame_awake_last_delivery_summary": delivered_summary,
            "frame_content_update_interval_minutes": frame_interval_minutes,
            "frame_ha_rotation_interval_seconds": frame_ha_rotation_seconds,
            "frame_wake_safety_cap_seconds": frame_wake_window_seconds,
            "selected_provider_id": metadata.get("selected_provider_id") or metadata.get("provider_id"),
            "display_rotation_enabled": metadata.get("display_rotation_enabled"),
            "display_rotation_interval_minutes": metadata.get("display_rotation_interval_minutes"),
            "frame_ha_config": frame_ha_config,
            "frame_schedule_enabled": frame_ha_config.get("scheduleEnabled", True) if frame_ha_config else None,
            "frame_interval_minutes": frame_interval_minutes,
            "frame_wake_window_seconds": frame_wake_window_seconds,
            "frame_max_jobs_per_wake": frame_awake.get("max_jobs_per_wake") or frame_ha_config.get("maxJobsPerWake"),
            "frame_ha_slot_csv": frame_ha_config.get("haSlotCsv"),
            "frame_ha_rotation_enabled": frame_ha_config.get("haRotationEnabled"),
            "frame_ha_rotation_seconds": frame_ha_rotation_seconds,
            "ha_rotation": metadata.get("ha_rotation"),
            "frame_awake_last_received_at": metadata.get("frame_awake_last_received_at"),
            "frame_awake_last_success_at": metadata.get("frame_awake_last_success_at"),
            "frame_sleeping_last_received_at": metadata.get("frame_sleeping_last_received_at"),
            "frame_awake": frame_awake,
            "frame_sleeping": metadata.get("frame_sleeping"),
            "last_error": metadata.get("last_error"),
        }


def _parse_iso_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _state_time_label(value: datetime) -> str:
    return value.strftime("%H:%M:%S")


def _delivered_job_count(metadata: dict) -> int:
    count = metadata.get("frame_content_last_delivered_count")
    if isinstance(count, int):
        return count
    jobs = metadata.get("frame_awake_last_delivered_jobs")
    if isinstance(jobs, list):
        return len(jobs)
    return 0


def _delivered_provider_ids(metadata: dict) -> list[str]:
    jobs = metadata.get("frame_awake_last_delivered_jobs")
    if not isinstance(jobs, list):
        return []
    provider_ids: list[str] = []
    for job in jobs:
        if isinstance(job, dict) and job.get("provider_id"):
            provider_ids.append(str(job["provider_id"]))
    return provider_ids


def _provider_display_name(provider_id: str) -> str:
    return PROVIDER_DISPLAY_NAMES.get(provider_id, provider_id.replace("_", " ").title())


def _delivered_summary(metadata: dict, provider_names: list[str]) -> str | None:
    count = _delivered_job_count(metadata)
    if count <= 0:
        return None
    if provider_names:
        return f"Sent {count} job{'s' if count != 1 else ''}: {', '.join(provider_names)}"
    return f"Sent {count} job{'s' if count != 1 else ''}"
