import pytest

from app.services.agent_runtime_flags import load_agent_runtime_flags, runtime_applies


@pytest.mark.parametrize('is_admin,expected', [(False, False), (True, True)])
def test_admin_only_runtime_apply(monkeypatch, is_admin, expected):
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ENABLED', 'true')
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ADMIN_ONLY', 'true')
    flags = load_agent_runtime_flags()
    assert runtime_applies(is_admin, flags) is expected
