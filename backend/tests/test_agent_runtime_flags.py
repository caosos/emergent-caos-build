from app.services.agent_runtime_flags import load_agent_runtime_flags, runtime_applies


def test_flags_default_off(monkeypatch):
    for k in [
        "CAOS_AGENT_RUNTIME_ENABLED",
        "CAOS_AGENT_RUNTIME_ADMIN_ONLY",
        "CAOS_PERMISSION_GATES_ENABLED",
        "CAOS_SESSION_LEDGER_ENABLED",
        "CAOS_SKILL_REGISTRY_ENABLED",
    ]:
        monkeypatch.delenv(k, raising=False)
    flags = load_agent_runtime_flags()
    assert flags.enabled is False
    assert flags.admin_only is False
    assert flags.permission_gates_enabled is False
    assert flags.session_ledger_enabled is False
    assert flags.skill_registry_enabled is False
    assert runtime_applies(is_admin_user=True, flags=flags) is False


def test_admin_only_behavior(monkeypatch):
    monkeypatch.setenv("CAOS_AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("CAOS_AGENT_RUNTIME_ADMIN_ONLY", "true")
    flags = load_agent_runtime_flags()
    assert runtime_applies(is_admin_user=False, flags=flags) is False
    assert runtime_applies(is_admin_user=True, flags=flags) is True
