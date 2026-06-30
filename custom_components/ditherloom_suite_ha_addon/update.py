from __future__ import annotations

import io
import json
import logging
import shutil
import zipfile
from datetime import timedelta
from typing import Any

from aiohttp import ClientError, ClientTimeout
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, INTEGRATION_VERSION

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=30)
GITHUB_REPOSITORY = "nacameron/ditherloom-suite-home-assistant-add-on-test"
LATEST_RELEASE_API_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
LATEST_RELEASE_URL = f"https://github.com/{GITHUB_REPOSITORY}/releases/latest"
REQUEST_TIMEOUT = ClientTimeout(total=15)
ZIPBALL_TIMEOUT = ClientTimeout(total=60)
MAX_ZIPBALL_BYTES = 30 * 1024 * 1024


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([DitherloomReleaseUpdate(hass, entry)], update_before_add=True)


class DitherloomReleaseUpdate(UpdateEntity):
    _attr_name = "Ditherloom integration update"
    _attr_supported_features = UpdateEntityFeature.RELEASE_NOTES | UpdateEntityFeature.INSTALL
    _attr_title = "Ditherloom Suite Home Assistant Add On"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_in_progress = False
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

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        target_version = (version or self.latest_version or "").strip()
        if not target_version:
            raise HomeAssistantError("No Ditherloom release version is available to install")

        self._attr_in_progress = True
        self.async_write_ha_state()
        try:
            zipball = await self._async_download_release_zipball(target_version)
            await self.hass.async_add_executor_job(_install_release_zipball, zipball)
            self._attr_installed_version = target_version
            self._attr_latest_version = target_version
        finally:
            self._attr_in_progress = False
            self.async_write_ha_state()

    async def _async_download_release_zipball(self, version: str) -> bytes:
        release_zip_url = f"https://github.com/{GITHUB_REPOSITORY}/archive/refs/tags/v{version}.zip"
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(
                release_zip_url,
                headers={"User-Agent": "Ditherloom-Suite-Home-Assistant-Add-On"},
                timeout=ZIPBALL_TIMEOUT,
            ) as response:
                if response.status != 200:
                    raise HomeAssistantError(f"Ditherloom release download returned HTTP {response.status}")
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_ZIPBALL_BYTES:
                    raise HomeAssistantError("Ditherloom release download is unexpectedly large")
                payload = await response.read()
        except (ClientError, TimeoutError, OSError) as exc:
            raise HomeAssistantError(f"Ditherloom release download failed: {exc}") from exc

        if len(payload) > MAX_ZIPBALL_BYTES:
            raise HomeAssistantError("Ditherloom release download is unexpectedly large")
        return payload


def _installed_version() -> str:
    return INTEGRATION_VERSION


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


def _install_release_zipball(zipball: bytes) -> None:
    component_dir = Path(__file__).resolve().parent
    component_prefix = "custom_components/ditherloom_suite_ha_addon/"

    try:
        with zipfile.ZipFile(io.BytesIO(zipball)) as archive:
            members = [
                member
                for member in archive.infolist()
                if component_prefix in member.filename.replace("\\", "/")
            ]
            if not members:
                raise HomeAssistantError("Ditherloom release did not contain the integration files")

            for member in members:
                normalized_name = member.filename.replace("\\", "/")
                relative_name = normalized_name.split(component_prefix, 1)[1]
                if not relative_name or relative_name.endswith("/"):
                    continue
                target = (component_dir / relative_name).resolve()
                if not target.is_relative_to(component_dir):
                    raise HomeAssistantError("Ditherloom release contained an invalid path")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
    except zipfile.BadZipFile as exc:
        raise HomeAssistantError("Ditherloom release download was not a valid zip file") from exc
