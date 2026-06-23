from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
            DitherloomRenderWeatherButton(coordinator, entry),
            DitherloomSendWeatherButton(coordinator, entry),
            DitherloomSyncWakeWindowButton(coordinator, entry),
        ]
    )


class DitherloomButtonBase(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ditherloom Suite Home Assistant Add On",
        )


class DitherloomRenderWeatherButton(DitherloomButtonBase):
    _attr_name = "Render weather preview"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_render_weather_preview"

    async def async_press(self) -> None:
        await self._coordinator.async_run_weather_action(
            {},
            publish=False,
            send_to_frame=False,
            action="render weather",
        )


class DitherloomSendWeatherButton(DitherloomButtonBase):
    _attr_name = "Send weather to frame"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_send_weather_to_frame"

    async def async_press(self) -> None:
        await self._coordinator.async_send_cached_weather_action()


class DitherloomSyncWakeWindowButton(DitherloomButtonBase):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Synchronise Wi-Fi wake window"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_sync_wake_window"

    async def async_press(self) -> None:
        await self._coordinator.async_sync_wake_window()
