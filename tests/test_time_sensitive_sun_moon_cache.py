from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py"


def test_sun_and_moon_cache_uses_frame_next_wake_render_target():
    source = INIT.read_text(encoding="utf-8")

    assert '"frame_next_wake_at"' in source
    assert "def _time_sensitive_render_target" in source
    assert "metadata[\"render_target_at\"] = render_target.isoformat()" in source
    assert "current_datetime=render_target" in source
    assert "metadata.get(\"frame_synced_render_target_at\") != metadata.get(\"render_target_at\")" in source


def test_sun_and_moon_are_not_daily_only_cached():
    source = INIT.read_text(encoding="utf-8")
    cache_start = source.index("def _cached_content_is_fresh")
    cache_end = source.index("def _local_timezone", cache_start)
    cache_source = source[cache_start:cache_end]

    assert 'metadata.get("date_label") == datetime.now(self._local_timezone()).strftime("%d %b").upper()' not in cache_source
    assert "return age < timedelta(minutes=self._time_sensitive_cache_minutes())" in cache_source
