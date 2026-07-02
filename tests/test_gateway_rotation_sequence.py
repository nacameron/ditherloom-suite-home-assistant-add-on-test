from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py"


def _source() -> str:
    return INIT.read_text(encoding="utf-8")


def test_gateway_upload_marks_slot_before_harotation():
    source = _source()
    upload_index = source.index("_upload_gateway_payload(sock_file, slot, packed, crc32)")
    mark_index = source.index("_ensure_gateway_slot_is_ha(sock_file, slot)", upload_index)
    rotation_index = source.index("_set_gateway_ha_rotation(sock_file", mark_index)

    assert upload_index < mark_index < rotation_index


def test_harotation_verifies_slots_before_enabling():
    source = _source()
    helper_index = source.index("def _set_gateway_ha_rotation")
    mark_index = source.index("_ensure_gateway_slot_is_ha(sock_file, slot)", helper_index)
    command_index = source.index('command = f"HAROTATION on', helper_index)
    send_index = source.index('_send_gateway_stage(sock_file, command, "HAROTATION")', helper_index)

    assert mark_index < command_index < send_index
    assert "HAROTATION failed or firmware rejected HA rotation slots" in source


def test_harotation_does_not_auto_claim_implicit_slots():
    source = _source()

    assert "missing_slots = [slot for slot in ha_rotation_slots if slot not in job_slots]" not in source
    assert "HA rotation slots have no uploaded provider payload" not in source
    assert "free" not in source[source.index("def _send_gateway_batch_jobs") : source.index("def _ensure_gateway_slot_is_ha")]


def test_gateway_success_requires_hacomplete_all_jobs_complete():
    source = _source()
    batch_start = source.index("def _send_gateway_batch_jobs")
    batch_end = source.index("def _ensure_gateway_slot_is_ha", batch_start)
    batch_source = source[batch_start:batch_end]
    completion_start = source.index("def _send_gateway_completion")
    completion_end = source.index("def _best_effort_open_connection_idle", completion_start)
    completion_source = source[completion_start:completion_end]

    assert "gateway_status[\"ha_completion\"] = _send_gateway_completion(sock_file)" in batch_source
    assert "_best_effort_open_connection_idle(sock_file)" not in batch_source.split("except Exception:", 1)[0]
    assert 'command = "HACOMPLETE all_jobs_complete"' in completion_source
    assert 'response = _send_gateway_stage(sock_file, command, "HACOMPLETE all_jobs_complete")' in completion_source
    assert 'response.startswith("OK HACOMPLETE")' in completion_source
    assert "HACOMPLETE all_jobs_complete failed" in completion_source


def test_frame_awake_reports_no_jobs_before_waiting_for_gateway_delivery():
    source = _source()
    awake_start = source.index("async def async_handle_frame_awake")
    awake_end = source.index("async def async_deliver_cached_content_to_announced_frame", awake_start)
    awake_source = source[awake_start:awake_end]

    assert "jobs = await self._frame_sync_jobs()" in awake_source
    assert 'self.last_status = "frame_awake_no_jobs"' in awake_source
    assert '"has_jobs": False' in awake_source
    assert '"job_count": 0' in awake_source
    assert "async_create_task(self.async_deliver_cached_content_to_announced_frame(host, port, target_slot, jobs))" in awake_source
    assert '"job_count": len(jobs)' in awake_source
    assert "async_publish_job" not in awake_source


def test_frame_awake_delivery_uses_precomputed_jobs_when_supplied():
    source = _source()
    delivery_start = source.index("async def async_deliver_cached_content_to_announced_frame")
    delivery_end = source.index("async def async_deliver_cached_weather_to_announced_frame", delivery_start)
    delivery_source = source[delivery_start:delivery_end]

    assert "jobs: list[dict[str, Any]] | None = None" in delivery_source
    assert "if jobs is None:" in delivery_source
    assert "jobs = await self._frame_sync_jobs()" in delivery_source
    assert "_send_gateway_batch_jobs, host, port, jobs, display_slot, ha_rotation" in delivery_source


def test_frame_sync_uses_content_id_not_provider_count_or_age_resend():
    source = _source()
    sync_start = source.index("def _provider_needs_frame_sync")
    sync_end = source.index("async def _mark_provider_frame_synced", sync_start)
    sync_source = source[sync_start:sync_end]
    mark_start = source.index("async def _mark_provider_frame_synced")
    mark_end = source.index("def _time_sensitive_cache_minutes", mark_start)
    mark_source = source[mark_start:mark_end]

    assert "content_id = metadata.get(ATTR_CONTENT_ID)" in sync_source
    assert 'metadata.get("frame_synced_content_id") != content_id' in sync_source
    assert "age >= timedelta(minutes=self._effective_update_interval_minutes())" not in sync_source
    assert 'metadata["frame_synced_content_id"] = metadata.get(ATTR_CONTENT_ID)' in mark_source


def test_harotation_can_apply_to_explicit_slots_without_fresh_upload_jobs():
    source = _source()
    batch_index = source.index("def _send_gateway_batch_jobs")
    rotation_index = source.index("_set_gateway_ha_rotation(sock_file", batch_index)
    helper_index = source.index("def _set_gateway_ha_rotation")
    mark_index = source.index("_ensure_gateway_slot_is_ha(sock_file, slot)", helper_index)

    assert batch_index < rotation_index < helper_index
    assert mark_index > helper_index


def test_harotation_is_not_reapplied_or_display_reset_when_already_active():
    source = _source()
    batch_start = source.index("def _send_gateway_batch_jobs")
    batch_end = source.index("def _ensure_gateway_slot_is_ha", batch_start)
    batch_source = source[batch_start:batch_end]

    assert "_harotation_state_matches(gateway_status[\"ha_rotation\"], rotation_seconds, ha_rotation_slots)" in batch_source
    assert "display_slot = None" in batch_source
    assert batch_source.index("_harotation_state_matches") < batch_source.index("_set_gateway_ha_rotation")


def test_harotation_slots_are_populated_enabled_provider_slots_in_physical_order():
    source = _source()
    config_start = source.index("def _ha_rotation_config")
    config_end = source.index("def _time_sensitive_render_target", config_start)
    config_source = source[config_start:config_end]
    batch_start = source.index("def _send_gateway_batch_jobs")
    batch_end = source.index("with socket.create_connection", batch_start)
    batch_source = source[batch_start:batch_end]

    assert "provider_slots = sorted(set(self._provider_slot_map().values()))" in config_source
    assert '"slots": provider_slots' in config_source
    assert "ha_rotation_slots = sorted(set(int(slot) for slot in (ha_rotation or {}).get(\"slots\", [])))" in batch_source
