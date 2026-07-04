from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import (
    CONF_FRAME_HA_SLOT_CSV,
    CONF_FRAME_HA_SLOT_POOL,
    CONF_FRAME_RESERVED_SLOT,
    CONF_DIESEL_SWEETIES_ENABLED,
    CONF_MIMI_EUNICE_ENABLED,
    CONF_MOON_ENABLED,
    CONF_SUN_ENABLED,
    CONF_TARGET_SLOT,
    CONF_WEATHER_ENABLED,
    CONF_XKCD_ENABLED,
    DEFAULT_TARGET_SLOT,
    DEVICE_SLOT_COUNT,
    MAX_HA_LANE_SLOTS,
)


PROVIDER_WEATHER = "open_meteo_weather"
PROVIDER_SUN = "sunrise_sunset"
PROVIDER_MOON = "moon_phase"
PROVIDER_XKCD = "xkcd_comic"
PROVIDER_DIESEL_SWEETIES = "diesel_sweeties"
PROVIDER_MIMI_EUNICE = "mimi_eunice"


@dataclass(frozen=True)
class HaLaneValidation:
    valid: bool
    error_key: str | None = None
    message: str = ""
    enabled_count: int = 0
    slot_count: int = 0
    suggested_pool: str = ""


def enabled_content_providers(options: dict[str, Any]) -> list[str]:
    providers: list[str] = []
    if _bool_option(options, CONF_WEATHER_ENABLED, True):
        providers.append(PROVIDER_WEATHER)
    if _bool_option(options, CONF_SUN_ENABLED, False):
        providers.append(PROVIDER_SUN)
    if _bool_option(options, CONF_MOON_ENABLED, False):
        providers.append(PROVIDER_MOON)
    if _bool_option(options, CONF_XKCD_ENABLED, False):
        providers.append(PROVIDER_XKCD)
    if _bool_option(options, CONF_DIESEL_SWEETIES_ENABLED, False):
        providers.append(PROVIDER_DIESEL_SWEETIES)
    if _bool_option(options, CONF_MIMI_EUNICE_ENABLED, False):
        providers.append(PROVIDER_MIMI_EUNICE)
    return providers or [PROVIDER_WEATHER]


def ha_lane_slots(options: dict[str, Any]) -> list[int]:
    frame_csv = options.get(CONF_FRAME_HA_SLOT_CSV)
    if frame_csv:
        return sorted(parse_slot_pool(frame_csv))
    if not _has_explicit_frame_slots(options):
        if _enabled_count(options) > 1:
            return []
        return [_slot_int(options.get(CONF_TARGET_SLOT), DEFAULT_TARGET_SLOT)]
    first = _slot_int(options.get(CONF_FRAME_RESERVED_SLOT), DEFAULT_TARGET_SLOT)
    slots = [first]
    for slot in parse_slot_pool(options.get(CONF_FRAME_HA_SLOT_POOL)):
        if slot not in slots:
            slots.append(slot)
    return sorted(slots)


def provider_slot_map(options: dict[str, Any]) -> dict[str, int]:
    validation = validate_ha_lane(options)
    if not validation.valid:
        raise ValueError(validation.message)
    providers = enabled_content_providers(options)
    slots = ha_lane_slots(options)
    return dict(zip(providers, slots))


def validate_ha_lane(options: dict[str, Any]) -> HaLaneValidation:
    providers = enabled_content_providers(options)
    slots = ha_lane_slots(options)
    if not slots:
        return HaLaneValidation(
            valid=False,
            error_key="frame_ha_slots_not_synced",
            message=(
                "Home Assistant has not received the frame HA slot setup yet. "
                "Connect to the Ditherloom app over Wi-Fi, configure the Home Assistant slots, "
                "save them to the frame, then come back and set up the Home Assistant providers."
            ),
            enabled_count=len(providers),
            slot_count=0,
        )
    if len(slots) > MAX_HA_LANE_SLOTS:
        return HaLaneValidation(
            valid=False,
            error_key="too_many_ha_slots",
            message=f"Home Assistant supports up to {MAX_HA_LANE_SLOTS} explicit HA slots.",
            enabled_count=len(providers),
            slot_count=len(slots),
        )
    if len(slots) < len(providers):
        reserved = _slot_int(options.get(CONF_FRAME_RESERVED_SLOT, options.get(CONF_TARGET_SLOT)), DEFAULT_TARGET_SLOT)
        suggested = suggest_slot_pool(reserved, len(providers) - 1)
        message = (
            f"You have {len(providers)} enabled content providers but the frame has {len(slots)} HA slot configured. "
            "Connect to the Ditherloom app over Wi-Fi, add extra HA slots, save them to the frame, "
            "then come back and set up the Home Assistant providers."
        )
        return HaLaneValidation(
            valid=False,
            error_key="not_enough_ha_slots",
            message=message,
            enabled_count=len(providers),
            slot_count=len(slots),
            suggested_pool=suggested,
        )
    return HaLaneValidation(valid=True, enabled_count=len(providers), slot_count=len(slots))


def parse_slot_pool(value: Any) -> list[int]:
    if value is None:
        return []
    slots: list[int] = []
    for part in str(value).replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = _slot_int(start_text, 0)
            end = _slot_int(end_text, 0)
            if start <= 0 or end <= 0:
                continue
            step = 1 if end >= start else -1
            for slot in range(start, end + step, step):
                if 1 <= slot <= DEVICE_SLOT_COUNT and slot not in slots:
                    slots.append(slot)
        else:
            slot = _slot_int(part, 0)
            if 1 <= slot <= DEVICE_SLOT_COUNT and slot not in slots:
                slots.append(slot)
    return slots


def slot_csv(slots: list[int]) -> str:
    return ",".join(str(slot) for slot in slots)


def suggest_slot_pool(reserved_slot: int, extra_count: int) -> str:
    if extra_count <= 0:
        return ""
    if reserved_slot + extra_count <= DEVICE_SLOT_COUNT:
        start = reserved_slot + 1
        end = reserved_slot + extra_count
    else:
        end = max(1, reserved_slot - 1)
        start = max(1, end - extra_count + 1)
    if start == end:
        return str(start)
    return f"{start}-{end}"


def _slot_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < 1 or parsed > DEVICE_SLOT_COUNT:
        return default
    return parsed


def _bool_option(options: dict[str, Any], key: str, default: bool) -> bool:
    return bool(options[key]) if key in options else default


def _enabled_count(options: dict[str, Any]) -> int:
    return len(enabled_content_providers(options))


def _has_explicit_frame_slots(options: dict[str, Any]) -> bool:
    return bool(
        options.get(CONF_FRAME_HA_SLOT_CSV)
        or options.get(CONF_FRAME_RESERVED_SLOT)
        or options.get(CONF_FRAME_HA_SLOT_POOL)
    )
