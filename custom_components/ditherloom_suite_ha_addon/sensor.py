from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


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
        if self._coordinator.last_status == "frame_awake_send_failed":
            return "delivery failed"
        if metadata.get("frame_awake_last_success_at"):
            return "delivered"
        if metadata.get("frame_awake_last_received_at"):
            return "frame awake"
        if metadata.get("content_refresh_last_success_at") or metadata.get("weather_refresh_last_success_at") or metadata.get("rendered_at"):
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
        return {
            "weather_refresh_next_at": metadata.get("weather_refresh_next_at"),
            "weather_refresh_interval_minutes": metadata.get("weather_refresh_interval_minutes"),
            "weather_refresh_last_success_at": metadata.get("weather_refresh_last_success_at"),
            "content_refresh_last_success_at": metadata.get("content_refresh_last_success_at"),
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
