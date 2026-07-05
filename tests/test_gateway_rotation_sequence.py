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


def test_frame_awake_success_metadata_requires_recorded_completion():
    source = _source()
    delivery_start = source.index("async def async_deliver_cached_content_to_announced_frame")
    delivery_end = source.index("async def async_deliver_cached_weather_to_announced_frame", delivery_start)
    delivery_source = source[delivery_start:delivery_end]

    assert "completion = gateway_status.get(\"ha_completion\") or {}" in delivery_source
    assert "Gateway delivery did not complete with HACOMPLETE all_jobs_complete" in delivery_source
    assert delivery_source.index("completion = gateway_status.get(\"ha_completion\") or {}") < delivery_source.index("self.last_status = \"frame_awake_sent\"")
    assert "self.last_metadata[\"frame_awake_last_completion_command\"] = completion.get(\"command\")" in delivery_source
    assert "self.last_metadata[\"frame_awake_last_completion_response\"] = completion.get(\"response\")" in delivery_source
    assert "self.last_metadata[\"frame_awake_last_completion_ok\"] = bool(completion.get(\"ok\"))" in delivery_source


def test_completion_proof_survives_later_content_refresh():
    source = _source()
    preserved_start = source.index("PRESERVED_RUNTIME_METADATA_KEYS = (")
    preserved_end = source.index("def _render_weather_artifact_to_disk", preserved_start)
    preserved_source = source[preserved_start:preserved_end]

    for key in (
        "frame_awake_last_completion_command",
        "frame_awake_last_completion_sent_at",
        "frame_awake_last_completion_response",
        "frame_awake_last_completion_ok",
        "frame_sleeping_expected_after_completion",
    ):
        assert key in preserved_source


def test_frame_awake_reports_no_jobs_before_waiting_for_gateway_delivery():
    source = _source()
    awake_start = source.index("async def async_handle_frame_awake")
    awake_end = source.index("async def async_deliver_cached_content_to_announced_frame", awake_start)
    awake_source = source[awake_start:awake_end]

    assert "jobs = await self._frame_sync_jobs()" in awake_source
    assert 'self.last_status = "frame_awake_no_jobs"' in awake_source
    assert '"has_jobs": False' in awake_source
    assert '"job_count": 0' in awake_source
    assert "async_create_task(self.async_deliver_cached_content_after_frame_callback(host, port, target_slot, jobs))" in awake_source
    assert '"mode": "gateway_push"' in awake_source
    assert '"has_jobs": True' in awake_source
    assert '"job_count": len(jobs)' in awake_source
    assert "async_publish_job" not in awake_source
    assert "payload_url" not in awake_source


def test_no_raw_payload_pull_endpoint_or_job_descriptor_remains():
    source = _source()

    forbidden = (
        "DitherloomPayloadView",
        "payloadPath",
        "payloadUrl",
        "payload_url",
        "async_publish_job",
        '"/payload/{filename}"',
        '"mode": "frame_pull"',
        "_frame_pull_job_descriptor",
        "frame_awake_pending_pull_jobs",
    )
    for text in forbidden:
        assert text not in source


def test_frame_awake_delivery_waits_for_callback_response_before_gateway_session():
    source = _source()
    delay_start = source.index("async def async_deliver_cached_content_after_frame_callback")
    delay_end = source.index("async def async_deliver_cached_content_to_announced_frame", delay_start)
    delay_source = source[delay_start:delay_end]

    assert "await asyncio.sleep(1.5)" in delay_source
    assert "await self.async_deliver_cached_content_to_announced_frame(host, port, target_slot, jobs)" in delay_source
    assert "single Gateway listener before HA opens the delivery" in delay_source


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


def test_provider_freshness_is_provider_specific():
    source = _source()
    fresh_start = source.index("def _cached_content_is_fresh")
    fresh_end = source.index("def _xkcd_cache_matches_options", fresh_start)
    fresh_source = source[fresh_start:fresh_end]
    xkcd_start = source.index("def _xkcd_cache_matches_options")
    xkcd_end = source.index("def _local_timezone", xkcd_start)
    xkcd_source = source[xkcd_start:xkcd_end]

    assert "if provider in {PROVIDER_SUN, PROVIDER_MOON}" in fresh_source
    assert "return True" in fresh_source
    assert "if provider == PROVIDER_XKCD" in fresh_source
    assert "if not self._xkcd_cache_matches_options(metadata):" in fresh_source
    assert "if self._comic_cache_was_delivered(provider, metadata):" in fresh_source
    assert "if provider in COMIC_SUCCESSOR_PROVIDERS and self._comic_cache_was_delivered(provider, metadata):" in fresh_source
    assert "if mode == XKCD_MODE_FIXED:" in fresh_source
    assert "age < timedelta(minutes=self._effective_update_interval_minutes())" in fresh_source
    assert "xkcd_mode" in xkcd_source
    assert "xkcd_configured_number" in xkcd_source
    assert "xkcd_random_attempts" in xkcd_source


def test_successful_delivery_prepares_comic_successor_cache_without_resend_loop():
    source = _source()
    delivery_start = source.index("async def async_deliver_cached_content_to_announced_frame")
    delivery_end = source.index("async def async_deliver_cached_weather_to_announced_frame", delivery_start)
    delivery_source = source[delivery_start:delivery_end]
    helper_start = source.index("async def _refresh_delivered_comic_successors")
    helper_end = source.index("def _time_sensitive_cache_minutes", helper_start)
    helper_source = source[helper_start:helper_end]

    assert "COMIC_SUCCESSOR_PROVIDERS = {PROVIDER_XKCD, PROVIDER_DIESEL_SWEETIES, PROVIDER_MIMI_EUNICE}" in source
    assert "self.hass.async_create_task(self._refresh_delivered_comic_successors(delivered_jobs, synced_at))" in delivery_source
    assert "previous_status = self.last_status" in helper_source
    assert "previous_metadata = dict(self.last_metadata)" in helper_source
    assert "rendered_successor = await self.async_render_provider_to_cache(provider)" in helper_source
    assert "self.last_status = previous_status" in helper_source
    assert "self.last_metadata = self._preserve_current_runtime_metadata(previous_metadata)" in helper_source
    assert "def _preserve_current_runtime_metadata" in helper_source
    assert "for key in PRESERVED_RUNTIME_METADATA_KEYS" in helper_source
    assert "rendered_successor.get(ATTR_CONTENT_ID) == delivered_content_id" in helper_source
    assert "rendered_successor[\"frame_synced_content_id\"] = delivered_content_id" in helper_source
    assert "self._record_delivered_comic_exclusions(delivered_jobs)" in delivery_source


def test_comic_renders_exclude_recently_delivered_content():
    source = _source()
    render_cache_start = source.index("async def async_render_provider_to_cache")
    render_cache_end = source.index("async def async_render_selected_content", render_cache_start)
    render_cache_source = source[render_cache_start:render_cache_end]
    webcomic_start = source.index("async def async_render_webcomic")
    webcomic_end = source.index("async def async_activate_cached_content", webcomic_start)
    webcomic_source = source[webcomic_start:webcomic_end]
    xkcd_start = source.index("def _render_xkcd_artifact_to_disk")
    xkcd_end = source.index("STALE_FRONTEND_ENTITY_UNIQUE_ID_SUFFIXES", xkcd_start)
    xkcd_source = source[xkcd_start:xkcd_end]
    exclusions_start = source.index("def _comic_render_exclusion_data")
    exclusions_end = source.index("def _local_timezone", exclusions_start)
    exclusions_source = source[exclusions_start:exclusions_end]

    assert "render_data = self._comic_render_exclusion_data(provider)" in render_cache_source
    assert "await self.async_render_xkcd(render_data" in render_cache_source
    assert "await self.async_render_webcomic(render_data" in render_cache_source
    assert "excluded_source_urls=excluded_urls" in webcomic_source
    assert "exclude_xkcd_numbers" in xkcd_source
    assert "xkcd fixed comic mode needs a comic number" in xkcd_source
    assert "already delivered and is stale for this frame slot" in xkcd_source
    assert "comic_delivery_exclusions" in exclusions_source
    assert "frame_awake_last_delivered_jobs" in exclusions_source


def test_refresh_continues_after_individual_provider_failure():
    source = _source()
    refresh_start = source.index("async def async_refresh_content_payload")
    refresh_end = source.index("async def async_render_provider_to_cache", refresh_start)
    refresh_source = source[refresh_start:refresh_end]

    assert "failed: dict[str, str] = {}" in refresh_source
    assert "except Exception as exc:" in refresh_source
    assert "failed[provider]" in refresh_source
    assert "continue" in refresh_source
    assert 'self.last_status = "content_refresh_partial" if failed else' in refresh_source


def test_frame_sync_skips_unavailable_provider_without_global_raise():
    source = _source()
    sync_start = source.index("async def _frame_sync_jobs")
    sync_end = source.index("def _provider_needs_frame_sync", sync_start)
    sync_source = source[sync_start:sync_end]

    assert "unavailable: dict[str, str] = {}" in sync_source
    assert 'unavailable[provider] = "missing"' in sync_source
    assert 'unavailable[provider] = "stale"' in sync_source
    assert "frame_awake_unavailable_providers" in sync_source
    assert "raise HomeAssistantError" not in sync_source
    assert "return jobs" in sync_source


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

    assert '"slots": self._active_provider_slots()' in config_source
    assert "ha_rotation_slots = sorted(set(int(slot) for slot in (ha_rotation or {}).get(\"slots\", [])))" in batch_source


def test_discovery_reports_configured_slots_and_active_provider_slots_separately():
    source = _source()
    owned_start = source.index("def _ha_owned_slots")
    owned_end = source.index("def _ha_slot_csv", owned_start)
    owned_source = source[owned_start:owned_end]
    rotation_start = source.index("def _ha_rotation_config")
    rotation_end = source.index("def _time_sensitive_render_target", rotation_start)
    rotation_source = source[rotation_start:rotation_end]
    frame_config_start = source.index("def _frame_provided_ha_config")
    frame_config_end = source.index("class DitherloomPreviewView", frame_config_start)
    frame_config_source = source[frame_config_start:frame_config_end]

    assert "return self._configured_ha_slots()" in owned_source
    assert '"slots": self._active_provider_slots()' in rotation_source
    assert "active_provider_slots(options)" in frame_config_source
    assert '"configuredHaSlotCsv": slot_csv(configured_slots)' in frame_config_source
    assert '"activeProviderSlotCsv": slot_csv(active_slots)' in frame_config_source
