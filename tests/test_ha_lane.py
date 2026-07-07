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
    CONF_ASTRONOMY_AURORA_WATCH_ENABLED,
    CONF_ASTRONOMY_CONDITIONS_ENABLED,
    CONF_ASTRONOMY_CONSTELLATION_ENABLED,
    CONF_ASTRONOMY_MOON_WATCH_ENABLED,
    CONF_ASTRONOMY_OVERHEAD_ENABLED,
    CONF_ASTRONOMY_SOLAR_ACTIVITY_ENABLED,
    CONF_ASTRONOMY_TONIGHT_SKY_ENABLED,
    CONF_ASTRONOMY_VISIBLE_PLANETS_ENABLED,
    CONF_COMICS_ENABLED,
    CONF_FRAME_HA_SLOT_CSV,
    CONF_FRAME_HA_SLOT_POOL,
    CONF_FRAME_RESERVED_SLOT,
    CONF_DIESEL_SWEETIES_ENABLED,
    CONF_IRREGULAR_WEBCOMIC_ENABLED,
    CONF_MIMI_EUNICE_ENABLED,
    CONF_MOON_ENABLED,
    CONF_PEPPER_CARROT_ENABLED,
    CONF_SUN_ENABLED,
    CONF_TARGET_SLOT,
    CONF_WEATHER_7_DAY_ENABLED,
    CONF_WEATHER_ENABLED,
    CONF_WEATHER_PRECIPITATION_ENABLED,
    CONF_WEATHER_RADAR_ENABLED,
    CONF_WEATHER_TODAY_TOMORROW_ENABLED,
    CONF_WEATHER_UV_ENABLED,
    CONF_WEATHER_WIND_ENABLED,
    CONF_XKCD_ENABLED,
)
from custom_components.ditherloom_suite_ha_addon.ha_lane import (
    active_provider_slots,
    enabled_content_providers,
    ha_lane_slots,
    parse_slot_pool,
    provider_slot_map,
    sanitize_provider_options,
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


def test_weather_subcards_are_separate_slot_providers():
    options = {
        CONF_FRAME_HA_SLOT_CSV: "440,441,442",
        CONF_WEATHER_ENABLED: True,
        CONF_WEATHER_TODAY_TOMORROW_ENABLED: True,
        CONF_WEATHER_7_DAY_ENABLED: True,
    }

    assert validate_ha_lane(options).valid
    assert enabled_content_providers(options) == [
        "open_meteo_weather",
        "open_meteo_today_tomorrow",
        "open_meteo_7_day_forecast",
    ]
    assert provider_slot_map(options) == {
        "open_meteo_weather": 440,
        "open_meteo_today_tomorrow": 441,
        "open_meteo_7_day_forecast": 442,
    }


def test_weather_metric_cards_are_separate_slot_providers():
    options = {
        CONF_FRAME_HA_SLOT_CSV: "440,441,442,443",
        CONF_WEATHER_RADAR_ENABLED: True,
        CONF_WEATHER_PRECIPITATION_ENABLED: True,
        CONF_WEATHER_UV_ENABLED: True,
        CONF_WEATHER_WIND_ENABLED: True,
    }

    assert validate_ha_lane(options).valid
    assert enabled_content_providers(options) == [
        "weather_radar",
        "open_meteo_precipitation",
        "open_meteo_uv",
        "open_meteo_wind",
    ]
    assert provider_slot_map(options) == {
        "weather_radar": 440,
        "open_meteo_precipitation": 441,
        "open_meteo_uv": 442,
        "open_meteo_wind": 443,
    }


def test_astronomy_cards_are_separate_slot_providers():
    options = {
        CONF_FRAME_HA_SLOT_CSV: "439,440,441,442,443,444,445,446",
        CONF_ASTRONOMY_VISIBLE_PLANETS_ENABLED: True,
        CONF_ASTRONOMY_MOON_WATCH_ENABLED: True,
        CONF_ASTRONOMY_CONSTELLATION_ENABLED: True,
        CONF_ASTRONOMY_TONIGHT_SKY_ENABLED: True,
        CONF_ASTRONOMY_OVERHEAD_ENABLED: True,
        CONF_ASTRONOMY_CONDITIONS_ENABLED: True,
        CONF_ASTRONOMY_SOLAR_ACTIVITY_ENABLED: True,
        CONF_ASTRONOMY_AURORA_WATCH_ENABLED: True,
    }

    assert validate_ha_lane(options).valid
    assert enabled_content_providers(options) == [
        "astronomy_visible_planets",
        "astronomy_moon_watch",
        "astronomy_constellation",
        "astronomy_tonight_sky",
        "astronomy_overhead",
        "astronomy_conditions",
        "astronomy_solar_activity",
        "astronomy_aurora_watch",
    ]
    assert provider_slot_map(options) == {
        "astronomy_visible_planets": 439,
        "astronomy_moon_watch": 440,
        "astronomy_constellation": 441,
        "astronomy_tonight_sky": 442,
        "astronomy_overhead": 443,
        "astronomy_conditions": 444,
        "astronomy_solar_activity": 445,
        "astronomy_aurora_watch": 446,
    }


def test_comic_providers_are_opt_in_and_consume_explicit_slots():
    options = {
        CONF_FRAME_HA_SLOT_CSV: "441,442,443",
        CONF_COMICS_ENABLED: True,
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


def test_disabled_comic_providers_release_previously_configured_slots():
    options = {
        CONF_FRAME_HA_SLOT_CSV: "441,442,443,444",
        CONF_WEATHER_ENABLED: True,
        CONF_XKCD_ENABLED: False,
        CONF_DIESEL_SWEETIES_ENABLED: False,
        CONF_MIMI_EUNICE_ENABLED: False,
    }

    assert ha_lane_slots(options) == [441, 442, 443, 444]
    assert provider_slot_map(options) == {"open_meteo_weather": 441}
    assert active_provider_slots(options) == [441]


def test_comics_framework_disabled_releases_saved_comic_flags():
    options = {
        CONF_FRAME_HA_SLOT_CSV: "438,439,440,441,442,443,444,445",
        CONF_COMICS_ENABLED: False,
        CONF_WEATHER_ENABLED: True,
        CONF_SUN_ENABLED: True,
        CONF_MOON_ENABLED: True,
        CONF_XKCD_ENABLED: True,
        CONF_DIESEL_SWEETIES_ENABLED: True,
        CONF_MIMI_EUNICE_ENABLED: True,
    }

    assert enabled_content_providers(options) == ["open_meteo_weather", "sunrise_sunset", "moon_phase"]
    assert validate_ha_lane(options).valid
    assert active_provider_slots(options) == [438, 439, 440]


def test_missing_weather_flag_does_not_consume_hidden_slot_when_other_providers_are_enabled():
    options = {
        CONF_FRAME_HA_SLOT_CSV: "438,439,440,441,442,443",
        CONF_COMICS_ENABLED: True,
        CONF_SUN_ENABLED: True,
        CONF_MOON_ENABLED: True,
        CONF_XKCD_ENABLED: True,
        CONF_DIESEL_SWEETIES_ENABLED: True,
        CONF_MIMI_EUNICE_ENABLED: True,
    }

    assert enabled_content_providers(options) == [
        "sunrise_sunset",
        "moon_phase",
        "xkcd_comic",
        "diesel_sweeties",
        "mimi_eunice",
    ]
    assert validate_ha_lane(options).valid


def test_missing_weather_flag_still_falls_back_to_weather_when_no_other_provider_is_enabled():
    assert enabled_content_providers({CONF_FRAME_HA_SLOT_CSV: "438"}) == ["open_meteo_weather"]
    assert validate_ha_lane({CONF_FRAME_HA_SLOT_CSV: "438"}).valid


def test_retired_comic_flags_are_ignored_for_slots():
    options = {
        CONF_FRAME_HA_SLOT_CSV: "438,439,440",
        CONF_WEATHER_ENABLED: True,
        CONF_PEPPER_CARROT_ENABLED: True,
        CONF_IRREGULAR_WEBCOMIC_ENABLED: True,
    }

    assert sanitize_provider_options(options)[CONF_PEPPER_CARROT_ENABLED] is False
    assert sanitize_provider_options(options)[CONF_IRREGULAR_WEBCOMIC_ENABLED] is False
    assert provider_slot_map(options) == {"open_meteo_weather": 438}


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


def test_more_than_eight_ha_slots_are_accepted_when_within_physical_capacity():
    result = validate_ha_lane({CONF_FRAME_RESERVED_SLOT: 439, CONF_FRAME_HA_SLOT_POOL: "440-446"})

    assert result.valid
    assert ha_lane_slots({CONF_FRAME_HA_SLOT_CSV: "439,440-446"}) == [439, 440, 441, 442, 443, 444, 445, 446]


def test_reserved_slots_can_span_the_full_physical_capacity():
    result = validate_ha_lane({CONF_FRAME_HA_SLOT_CSV: "1-446"})

    assert result.valid
    assert result.slot_count == 446
    assert ha_lane_slots({CONF_FRAME_HA_SLOT_CSV: "1,2-446"})[0] == 1
    assert ha_lane_slots({CONF_FRAME_HA_SLOT_CSV: "1,2-446"})[-1] == 446


def test_slots_outside_physical_capacity_are_ignored():
    result = validate_ha_lane({CONF_FRAME_RESERVED_SLOT: 438, CONF_FRAME_HA_SLOT_POOL: "439-447"})

    assert result.valid
    assert 447 not in ha_lane_slots({CONF_FRAME_RESERVED_SLOT: 438, CONF_FRAME_HA_SLOT_POOL: "439-447"})


def test_configured_reserved_capacity_stays_separate_from_active_provider_slots():
    result = validate_ha_lane({CONF_FRAME_RESERVED_SLOT: 438, CONF_FRAME_HA_SLOT_POOL: "439-446"})

    assert result.valid
    assert result.slot_count == 9
    assert ha_lane_slots({CONF_FRAME_RESERVED_SLOT: 438, CONF_FRAME_HA_SLOT_POOL: "439-446"}) == [
        438,
        439,
        440,
        441,
        442,
        443,
        444,
        445,
        446,
    ]
    assert active_provider_slots({CONF_FRAME_RESERVED_SLOT: 438, CONF_FRAME_HA_SLOT_POOL: "439-446"}) == [438]
