from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from aiohttp import ClientError, ClientTimeout
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=6)
GITHUB_REPOSITORY = "nacameron/ditherloom-suite-home-assistant-add-on-test"
LATEST_RELEASE_API_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
LATEST_RELEASE_URL = f"https://github.com/{GITHUB_REPOSITORY}/releases/latest"
REQUEST_TIMEOUT = ClientTimeout(total=15)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([DitherloomReleaseUpdate(hass, entry)], update_before_add=True)


class DitherloomReleaseUpdate(UpdateEntity):
    _attr_name = "Ditherloom integration update"
    _attr_supported_features = UpdateEntityFeature.RELEASE_NOTES
    _attr_title = "Ditherloom Suite Home Assistant Add On"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._release_notes: str | None = None
        installed_version = _installed_version()
        self._attr_installed_version = installed_version
        self._attr_latest_version = installed_version
        self._attr_release_url = LATEST_RELEASE_URL
        self._attr_unique_id = f"{entry.entry_id}_ditherloom_release_update"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ditherloom Suite Home Assistant Add On",
        )

    async def async_update(self) -> None:
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(
                LATEST_RELEASE_API_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "Ditherloom-Suite-Home-Assistant-Add-On",
                },
                timeout=REQUEST_TIMEOUT,
            ) as response:
                if response.status != 200:
                    _LOGGER.debug("GitHub release check returned HTTP %s", response.status)
                    return
                payload = await response.json()
        except (ClientError, TimeoutError, json.JSONDecodeError) as exc:
            _LOGGER.debug("GitHub release check failed: %s", exc)
            return

        latest_version = _version_from_tag(payload.get("tag_name"))
        if not latest_version:
            _LOGGER.debug("GitHub release check did not include a usable tag_name")
            return

        self._attr_latest_version = latest_version
        self._attr_release_url = str(payload.get("html_url") or LATEST_RELEASE_URL)
        self._attr_release_summary = _release_summary(payload)
        self._release_notes = _release_notes(payload)

    async def async_release_notes(self) -> str | None:
        return self._release_notes


def _installed_version() -> str:
    manifest_path = Path(__file__).with_name("manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "0.0.0"
    version = manifest.get("version")
    return str(version) if version else "0.0.0"


def _version_from_tag(tag: Any) -> str | None:
    if not isinstance(tag, str):
        return None
    tag = tag.strip()
    if not tag:
        return None
    return tag[1:] if tag.lower().startswith("v") else tag


def _release_summary(payload: dict[str, Any]) -> str | None:
    body = str(payload.get("body") or "").strip()
    if not body:
        return str(payload.get("name") or "").strip() or None
    first_line = next((line.strip(" -#") for line in body.splitlines() if line.strip()), "")
    return first_line[:255] if first_line else None


def _release_notes(payload: dict[str, Any]) -> str | None:
    body = str(payload.get("body") or "").strip()
    if body:
        return body
    name = str(payload.get("name") or "").strip()
    return name or None
