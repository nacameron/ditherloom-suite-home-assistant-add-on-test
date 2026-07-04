from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import (
    COMICS_SLOT_MODE_ALTERNATE,
    COMICS_SLOT_MODE_PER_SOURCE,
    CONF_COMICS_ENABLED,
    CONF_COMICS_SLOT_MODE,
    CONF_DIESEL_SWEETIES_ENABLED,
    CONF_MIMI_EUNICE_ENABLED,
    CONF_XKCD_ENABLED,
    DEFAULT_COMICS_SLOT_MODE,
)

COMIC_SOURCE_XKCD = "xkcd"
COMIC_PROVIDER_XKCD = "xkcd_comic"
COMIC_SOURCE_DIESEL_SWEETIES = "diesel_sweeties"
COMIC_PROVIDER_DIESEL_SWEETIES = "diesel_sweeties"
COMIC_SOURCE_MIMI_EUNICE = "mimi_eunice"
COMIC_PROVIDER_MIMI_EUNICE = "mimi_eunice"
COMIC_FAMILY_PROVIDER = "comics"


@dataclass(frozen=True)
class ComicSource:
    source_id: str
    provider_id: str
    name: str
    attribution: str
    attribution_url: str
    license_name: str
    license_url: str
    enabled_option: str
    implemented: bool = False


COMIC_SOURCES: tuple[ComicSource, ...] = (
    ComicSource(
        source_id=COMIC_SOURCE_XKCD,
        provider_id=COMIC_PROVIDER_XKCD,
        name="xkcd Comic",
        attribution="xkcd / Randall Munroe | CC BY-NC 2.5",
        attribution_url="https://xkcd.com/license.html",
        license_name="CC BY-NC 2.5",
        license_url="https://creativecommons.org/licenses/by-nc/2.5/",
        enabled_option=CONF_XKCD_ENABLED,
        implemented=True,
    ),
    ComicSource(
        source_id=COMIC_SOURCE_DIESEL_SWEETIES,
        provider_id=COMIC_PROVIDER_DIESEL_SWEETIES,
        name="Diesel Sweeties",
        attribution="Diesel Sweeties / R. Stevens | CC BY-NC",
        attribution_url="https://www.dieselsweeties.com/",
        license_name="CC BY-NC",
        license_url="https://creativecommons.org/licenses/by-nc/2.5/",
        enabled_option=CONF_DIESEL_SWEETIES_ENABLED,
        implemented=True,
    ),
    ComicSource(
        source_id=COMIC_SOURCE_MIMI_EUNICE,
        provider_id=COMIC_PROVIDER_MIMI_EUNICE,
        name="Mimi & Eunice",
        attribution="Mimi & Eunice / Nina Paley | CC BY-SA",
        attribution_url="https://mimiandeunice.com/about/",
        license_name="CC BY-SA",
        license_url="https://creativecommons.org/licenses/by-sa/3.0/",
        enabled_option=CONF_MIMI_EUNICE_ENABLED,
        implemented=True,
    ),
)

COMIC_SOURCE_BY_ID = {source.source_id: source for source in COMIC_SOURCES}
COMIC_SOURCE_BY_PROVIDER_ID = {source.provider_id: source for source in COMIC_SOURCES}
COMICS_RENDER_CONTRACT = (
    "Every comic source must fetch candidates, pass each candidate through "
    "comics_selector.select_best_comic_candidate, render through the shared "
    "400x300 comic renderer contract, store source-specific attribution/license "
    "metadata, and then use the existing HA cached payload delivery path."
)


def comics_enabled(options: dict[str, Any]) -> bool:
    return bool(options.get(CONF_COMICS_ENABLED, False))


def comics_slot_mode(options: dict[str, Any]) -> str:
    mode = str(options.get(CONF_COMICS_SLOT_MODE, DEFAULT_COMICS_SLOT_MODE))
    if mode == COMICS_SLOT_MODE_PER_SOURCE:
        return COMICS_SLOT_MODE_PER_SOURCE
    return COMICS_SLOT_MODE_ALTERNATE


def enabled_comic_sources(options: dict[str, Any], *, include_legacy: bool = True) -> list[ComicSource]:
    if not comics_enabled(options) and not include_legacy:
        return []
    if not comics_enabled(options) and not any(bool(options.get(source.enabled_option, False)) for source in COMIC_SOURCES):
        return []
    return [source for source in COMIC_SOURCES if bool(options.get(source.enabled_option, False))]


def comic_provider_ids(options: dict[str, Any]) -> list[str]:
    sources = enabled_comic_sources(options)
    if not sources:
        return []
    if comics_enabled(options) and comics_slot_mode(options) == COMICS_SLOT_MODE_ALTERNATE:
        return [COMIC_FAMILY_PROVIDER]
    return [source.provider_id for source in sources]


def comics_framework_attributes(options: dict[str, Any]) -> dict[str, Any]:
    enabled_sources = enabled_comic_sources(options)
    return {
        "comics_enabled": comics_enabled(options),
        "comics_slot_mode": comics_slot_mode(options),
        "enabled_comic_sources": [source.source_id for source in enabled_sources],
        "enabled_comic_provider_ids": comic_provider_ids(options),
        "available_comic_sources": [
            {
                "source_id": source.source_id,
                "provider_id": source.provider_id,
                "name": source.name,
                "implemented": source.implemented,
                "attribution": source.attribution,
                "attribution_url": source.attribution_url,
                "license": source.license_name,
                "license_url": source.license_url,
            }
            for source in COMIC_SOURCES
        ],
        "framework_note": (
            "The Comics framework owns comic-source configuration. "
            "xkcd remains on the proven xkcd_comic provider, cache, render, and delivery path."
        ),
        "render_contract": COMICS_RENDER_CONTRACT,
    }
