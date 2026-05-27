from pathlib import Path


def test_hook_exists_and_precedes_quota_check():
    src = Path('backend/app/services/chat_pipeline.py').read_text(encoding='utf-8')
    assert 'run_agent_preflight(' in src
    assert src.index('run_agent_preflight(') < src.index('estimated_tokens = 2000')


def test_hook_is_compact_under_20_lines_inside_run_chat_turn():
    lines = Path('backend/app/services/chat_pipeline.py').read_text(encoding='utf-8').splitlines()
    start = next(i for i, line in enumerate(lines) if 'preflight = await run_agent_preflight' in line)
    end = next(i for i, line in enumerate(lines[start:], start=start) if 'estimated_tokens = 2000' in line)
    assert (end - start) <= 20


def test_runtime_error_response_redacts_secret_detail():
    src = Path('backend/app/services/chat_pipeline.py').read_text(encoding='utf-8')
    assert 'from app.services.agent_secret_redaction import redact_secrets' in src
    assert 'safe_detail = str(redact_secrets(detail or ""))[:200]' in src


def test_preflight_exception_fails_closed_no_legacy_fallback():
    src = Path('backend/app/services/chat_pipeline.py').read_text(encoding='utf-8')
    assert 'except Exception as preflight_error:' in src
    assert 'return _runtime_error_response(payload, str(preflight_error))' in src
