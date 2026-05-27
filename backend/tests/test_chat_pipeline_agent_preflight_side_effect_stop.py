import asyncio
import pytest

from app.services.agent_runtime_preflight import run_agent_preflight


@pytest.mark.parametrize('text', [
    'please edit code in this repo and open pull request',
    'send email to customer about outage',
    'create calendar event for tomorrow',
    'remember this user preference forever',
])
def test_side_effect_intents_block(text, monkeypatch):
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ENABLED', 'true')
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ADMIN_ONLY', 'false')
    result = asyncio.run(run_agent_preflight(user_text=text, is_admin_user=True, session_id='s1'))
    assert result.allow_execute is False
    assert result.requires_approval is True
    assert result.is_side_effect is True
    assert result.fallback_allowed is False


def test_unknown_intent_does_not_fallback(monkeypatch):
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ENABLED', 'true')
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ADMIN_ONLY', 'false')
    result = asyncio.run(run_agent_preflight(user_text='blorb glorb flarn', is_admin_user=True, session_id='s2'))
    assert result.allow_execute is False
    assert result.classification_known is False
    assert result.fallback_allowed is False


def test_preflight_failure_before_classification_no_fallback(monkeypatch):
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ENABLED', 'true')
    monkeypatch.setenv('CAOS_AGENT_RUNTIME_ADMIN_ONLY', 'false')

    from app.services import agent_runtime_preflight as mod

    def boom(_):
        raise RuntimeError('broken classifier')

    monkeypatch.setattr(mod, 'classify_request_intent', boom)
    with pytest.raises(RuntimeError):
        asyncio.run(run_agent_preflight(user_text='check status', is_admin_user=True, session_id='s3'))
