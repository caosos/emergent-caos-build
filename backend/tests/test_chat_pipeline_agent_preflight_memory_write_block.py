import asyncio

from app.services.agent_runtime_preflight import run_agent_preflight


def test_memory_write_intent_blocks(monkeypatch):
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ENABLED', 'true')
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ADMIN_ONLY', 'false')
    result = asyncio.run(run_agent_preflight(user_text='write memory that I like tea', is_admin_user=True, session_id='m1'))
    assert result.requires_approval is True
    assert result.is_side_effect is True


def test_read_only_preflight_allows_and_can_fallback(monkeypatch):
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ENABLED', 'true')
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ADMIN_ONLY', 'false')
    result = asyncio.run(run_agent_preflight(user_text='check my github repo and report what needs attention', is_admin_user=True, session_id='m2'))
    assert result.allow_execute is True
    assert result.is_side_effect is False
    assert result.classification_known is True
    assert result.fallback_allowed is True
