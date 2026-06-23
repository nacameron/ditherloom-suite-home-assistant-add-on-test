from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DitherloomWeatherPreviewImage(coordinator, entry)])


class DitherloomWeatherPreviewImage(ImageEntity):
    _attr_content_type = "image/png"
    _attr_has_entity_name = True
    _attr_name = "Weather preview"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator.hass)
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_weather_preview"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ditherloom Suite Home Assistant Add On",
        )

    @property
    def image_last_updated(self) -> datetime | None:
        rendered_at = self._coordinator.last_metadata.get("rendered_at")
        if isinstance(rendered_at, str):
            try:
                return datetime.fromisoformat(rendered_at)
            except ValueError:
                return None
        return None

    async def async_image(self) -> bytes | None:
        path = self._coordinator.preview_path()
        if not path.exists():
            return None
        return await self.hass.async_add_executor_job(path.read_bytes)
