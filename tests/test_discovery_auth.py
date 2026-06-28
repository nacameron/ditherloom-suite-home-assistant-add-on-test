from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "custom_components" / "ditherloom_suite_ha_addon" / "__init__.py"


def test_discovery_auth_accepts_current_home_assistant_sync_validator_shape():
    source = INIT.read_text(encoding="utf-8")
    assert "import inspect" in source
    assert "result = validator(token)" in source
    assert "if inspect.isawaitable(result):" in source
    assert "result = await result" in source
    assert "return result is not None" in source
    assert "await validator(token)" not in source

