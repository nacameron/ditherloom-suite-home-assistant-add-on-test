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

    assert "missing_slots = [slot for slot in ha_rotation_slots if slot not in job_slots]" in source
    assert "HA rotation slots have no uploaded provider payload" in source
    assert "free" not in source[source.index("def _send_gateway_batch_jobs") : source.index("def _ensure_gateway_slot_is_ha")]
