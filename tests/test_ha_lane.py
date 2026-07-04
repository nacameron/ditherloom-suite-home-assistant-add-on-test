import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

ditherloom_package = types.ModuleType("custom_components.ditherloom_suite_ha_addon")
ditherloom_package.__path__ = [str(ROOT / "custom_components" / "ditherloom_suite_ha_addon")]
sys.modules.setdefault("custom_components.ditherloom_suite_ha_addon", ditherloom_package)

from custom_components.ditherloom_suite_ha_addon.const import (
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
)
from custom_components.ditherloom_suite_ha_addon.ha_lane import (
    ha_lane_slots,
    parse_slot_pool,
    provider_slot_map,
    validate_ha_lane,
)


def test_slot_validation_passes_with_one_provider_and_reserved_slot():
    result = validate_ha_lane({CONF_TARGET_SLOT: 445, CONF_WEATHER_ENABLED: True})

    assert result.valid
    assert result.enabled_count == 1
    assert result.slot_count == 1


def test_slot_validation_fails_with_three_providers_and_one_slot():
    result = validate_ha_lane(
        {
            CONF_FRAME_RESERVED_SLOT: 445,
            CONF_WEATHER_ENABLED: True,
            CONF_SUN_ENABLED: True,
            CONF_MOON_ENABLED: True,
        }
    )

    assert not result.valid
    assert result.error_key == "not_enough_ha_slots"
    assert "3 enabled content providers" in result.message
    assert "Ditherloom app over Wi-Fi" in result.message


def test_xkcd_provider_is_opt_in_and_consumes_explicit_slot():
    options = {
        CONF_FRAME_HA_SLOT_CSV: "443,444",
        CONF_WEATHER_ENABLED: True,
        CONF_XKCD_ENABLED: True,
    }

    result = validate_ha_lane(options)

    assert result.valid
    assert provider_slot_map(options) == {
        "open_meteo_weather": 443,
        "xkcd_comic": 444,
    }


def test_comic_providers_are_opt_in_and_consume_explicit_slots():
    options = {
        CONF_FRAME_HA_SLOT_CSV: "441,442,443",
        CONF_WEATHER_ENABLED: True,
        CONF_DIESEL_SWEETIES_ENABLED: True,
        CONF_MIMI_EUNICE_ENABLED: True,
    }

    result = validate_ha_lane(options)

    assert result.valid
    assert provider_slot_map(options) == {
        "open_meteo_weather": 441,
        "diesel_sweeties": 442,
        "mimi_eunice": 443,
    }


def test_slot_validation_fails_with_multiple_providers_without_frame_sync():
    result = validate_ha_lane(
        {
            CONF_WEATHER_ENABLED: True,
            CONF_SUN_ENABLED: True,
        }
    )

    assert not result.valid
    assert result.error_key == "frame_ha_slots_not_synced"
    assert "save them to the frame" in result.message


def test_slot_validation_passes_with_three_providers_and_frame_pool_range():
    result = validate_ha_lane(
        {
            CONF_FRAME_RESERVED_SLOT: 445,
            CONF_FRAME_HA_SLOT_POOL: "443-444",
            CONF_WEATHER_ENABLED: True,
            CONF_SUN_ENABLED: True,
            CONF_MOON_ENABLED: True,
        }
    )

    assert result.valid
    assert provider_slot_map(
        {
            CONF_FRAME_RESERVED_SLOT: 445,
            CONF_FRAME_HA_SLOT_POOL: "443-444",
            CONF_WEATHER_ENABLED: True,
            CONF_SUN_ENABLED: True,
            CONF_MOON_ENABLED: True,
        }
    ) == {
        "open_meteo_weather": 443,
        "sunrise_sunset": 444,
        "moon_phase": 445,
    }


def test_ha_lane_slots_are_sorted_in_ascending_physical_order():
    assert ha_lane_slots({CONF_FRAME_RESERVED_SLOT: 445, CONF_FRAME_HA_SLOT_POOL: "443-444"}) == [443, 444, 445]
    assert ha_lane_slots({CONF_FRAME_HA_SLOT_CSV: "445,443,444"}) == [443, 444, 445]


def test_slot_pool_parsing_supports_commas_and_ranges():
    assert parse_slot_pool("443,444-446,443") == [443, 444, 445, 446]


def test_up_to_eight_ha_slots_are_accepted():
    result = validate_ha_lane({CONF_FRAME_RESERVED_SLOT: 439, CONF_FRAME_HA_SLOT_POOL: "440-446"})

    assert result.valid
    assert ha_lane_slots({CONF_FRAME_HA_SLOT_CSV: "439,440-446"}) == [439, 440, 441, 442, 443, 444, 445, 446]


def test_more_than_eight_ha_slots_are_rejected():
    result = validate_ha_lane({CONF_FRAME_RESERVED_SLOT: 438, CONF_FRAME_HA_SLOT_POOL: "439-446"})

    assert not result.valid
    assert result.error_key == "too_many_ha_slots"
