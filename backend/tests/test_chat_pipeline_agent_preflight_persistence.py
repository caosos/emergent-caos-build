from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHAT_PIPELINE = _REPO_ROOT / "backend" / "app" / "services" / "chat_pipeline.py"


def _src() -> str:
    return _CHAT_PIPELINE.read_text(encoding="utf-8")


def test_preflight_persistence_hooks_present_and_compact():
    src = _src()
    assert "persist_runtime_preflight_outcome" in src
    assert "persist_runtime_preflight_error" in src
    lines = src.splitlines()
    start = next(i for i, line in enumerate(lines) if "preflight = await run_agent_preflight" in line)
    end = next(i for i, line in enumerate(lines[start:], start=start) if "estimated_tokens = 2000" in line)
    assert (end - start) <= 30


def test_blocked_response_still_precedes_quota_provider_paths():
    src = _src()
    blocked_idx = src.index("if preflight.requires_approval or (not preflight.allow_execute) or (not preflight.classification_known):")
    quota_idx = src.index("estimated_tokens = 2000")
    runtime_idx = src.index("runtime = resolve_chat_runtime")
    assert blocked_idx < quota_idx
    assert blocked_idx < runtime_idx


def test_preflight_persistence_failure_is_non_fatal():
    src = _src()
    assert "except Exception:\n            pass" in src
