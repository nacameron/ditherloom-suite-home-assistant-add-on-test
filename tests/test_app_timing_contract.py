from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py"
SENSOR = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "sensor.py"
CONST = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "const.py"


def test_discovery_preserves_app_frame_timing_fields():
    source = INIT.read_text(encoding="utf-8")
    const_source = CONST.read_text(encoding="utf-8")

    assert 'CONF_FRAME_INTERVAL_MINUTES = "frame_interval_minutes"' in const_source
    assert 'if "intervalMinutes" in body:' in source
    assert "updates[CONF_FRAME_INTERVAL_MINUTES] = interval_minutes" in source
    assert 'if "haRotationSeconds" in body:' in source
    assert "updates[CONF_FRAME_HA_ROTATION_SECONDS] = seconds" in source
    assert 'if "wakeWindowSeconds" in body:' in source
    assert "updates[CONF_WAKE_WINDOW_SECONDS] = wake_window_seconds" in source
    assert '"intervalMinutes": self._frame_interval_minutes()' in source
    assert '"haRotationSeconds": self._ha_rotation_seconds()' in source
    assert '"wakeWindowSeconds": self._effective_wake_window_seconds()' in source


def test_wake_window_is_not_used_as_refresh_or_rotation_interval():
    source = INIT.read_text(encoding="utf-8")
    update_start = source.index("def _effective_update_interval_minutes")
    update_end = source.index("def _effective_wake_window_seconds", update_start)
    rotation_start = source.index("def _ha_rotation_seconds")
    rotation_end = source.index("def _ha_rotation_config", rotation_start)

    assert "CONF_WAKE_WINDOW" not in source[update_start:update_end]
    assert "CONF_WAKE_WINDOW" not in source[rotation_start:rotation_end]


def test_sensor_attributes_expose_distinct_timing_meanings():
    source = SENSOR.read_text(encoding="utf-8")

    assert '"frame_content_update_interval_minutes": frame_interval_minutes' in source
    assert '"frame_ha_rotation_interval_seconds": frame_ha_rotation_seconds' in source
    assert '"frame_wake_safety_cap_seconds": frame_wake_window_seconds' in source
    assert 'frame_interval_minutes = frame_ha_config.get("intervalMinutes")' in source
    assert 'frame_ha_rotation_seconds = frame_ha_config.get("haRotationSeconds")' in source
    assert 'frame_wake_window_seconds = frame_awake.get("wake_window_seconds") or frame_ha_config.get("wakeWindowSeconds")' in source

