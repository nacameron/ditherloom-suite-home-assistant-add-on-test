from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import (
    CONF_HA_SLOT_POOL,
    CONF_MOON_ENABLED,
    CONF_SUN_ENABLED,
    CONF_TARGET_SLOT,
    CONF_WEATHER_ENABLED,
    DEFAULT_TARGET_SLOT,
    DEVICE_SLOT_COUNT,
    MAX_HA_LANE_SLOTS,
)


PROVIDER_WEATHER = "open_meteo_weather"
PROVIDER_SUN = "sunrise_sunset"
PROVIDER_MOON = "moon_phase"


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
    return providers or [PROVIDER_WEATHER]


def ha_lane_slots(options: dict[str, Any]) -> list[int]:
    first = _slot_int(options.get(CONF_TARGET_SLOT), DEFAULT_TARGET_SLOT)
    slots = [first]
    for slot in parse_slot_pool(options.get(CONF_HA_SLOT_POOL)):
        if slot not in slots:
            slots.append(slot)
    return slots


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
    if len(slots) > MAX_HA_LANE_SLOTS:
        return HaLaneValidation(
            valid=False,
            error_key="too_many_ha_slots",
            message=f"Home Assistant supports up to {MAX_HA_LANE_SLOTS} explicit HA slots.",
            enabled_count=len(providers),
            slot_count=len(slots),
        )
    if len(slots) < len(providers):
        reserved = _slot_int(options.get(CONF_TARGET_SLOT), DEFAULT_TARGET_SLOT)
        suggested = suggest_slot_pool(reserved, len(providers) - 1)
        message = (
            f"You have {len(providers)} enabled content providers but only {len(slots)} HA slot configured. "
            f"Keep only one provider enabled, or set HA Slot Pool to {suggested}."
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


def ha_rotation_command(enabled: bool, seconds: int, slots: list[int]) -> str:
    if not enabled:
        return "HAROTATION off"
    if not slots:
        raise ValueError("HA rotation requires at least one HA-owned slot")
    if len(slots) > MAX_HA_LANE_SLOTS:
        raise ValueError(f"HA rotation supports up to {MAX_HA_LANE_SLOTS} HA-owned slots")
    slot_csv = ",".join(str(slot) for slot in slots)
    return f"HAROTATION on {max(60, int(seconds))} {slot_csv}"


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
