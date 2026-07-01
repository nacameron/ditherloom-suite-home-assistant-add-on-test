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
