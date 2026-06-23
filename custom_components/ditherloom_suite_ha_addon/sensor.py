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
    _attr_name = "Frame schedule status"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_frame_schedule_status"

    @property
    def native_value(self):
        metadata = self._coordinator.last_metadata
        frame_timer = metadata.get("frame_timer")
        if isinstance(frame_timer, dict) and frame_timer.get("schedule_enabled"):
            return "synced"
        if self._coordinator.last_status == "sync_window_waiting":
            return "waiting"
        return "not synced"

    @property
    def extra_state_attributes(self):
        metadata = self._coordinator.last_metadata
        return {
            "next_auto_send": metadata.get("auto_send_next_at"),
            "auto_send_window_expires_at": metadata.get("auto_send_window_expires_at"),
            "sync_window_started_at": metadata.get("sync_window_started_at"),
            "sync_window_expires_at": metadata.get("sync_window_expires_at"),
            "frame_timer": metadata.get("frame_timer"),
            "last_error": metadata.get("last_error"),
        }
