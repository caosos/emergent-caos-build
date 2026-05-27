import asyncio
import sys
import types

from app.schemas.agent_runtime import AgentPreflightResult, AgentRuntimeFlags

_fake_db = types.ModuleType("app.db")
_fake_db.collection = lambda _name: None
sys.modules.setdefault("app.db", _fake_db)

from app.services import agent_runtime_persistence as mod


def _flags(**kwargs):
    base = dict(enabled=True, session_ledger_enabled=True, approval_persistence_enabled=False, runtime_receipts_enabled=False)
    base.update(kwargs)
    return AgentRuntimeFlags(**base)


def test_no_persistence_when_runtime_disabled(monkeypatch):
    called = {"session": 0}

    async def fake_create(_):
        called["session"] += 1

    monkeypatch.setattr(mod, "create_agent_session", fake_create)
    asyncio.run(mod.persist_runtime_preflight_outcome(flags=_flags(enabled=False), preflight=AgentPreflightResult(allow_execute=True), payload_session_id="s1", chat_session_id="s1", user_email="u@e.com", user_id=None, user_request="read status"))
    assert called["session"] == 0


def test_read_only_ledger_only_when_enabled(monkeypatch):
    called = {"session": 0, "approval": 0}

    async def fake_create(_):
        called["session"] += 1

    async def fake_approval(**_):
        called["approval"] += 1

    monkeypatch.setattr(mod, "create_agent_session", fake_create)
    monkeypatch.setattr(mod, "create_approval_item", fake_approval)

    pf = AgentPreflightResult(allow_execute=True, classification_known=True, is_side_effect=False, requires_approval=False, receipt_fragment={"output_summary": "read_only"})
    asyncio.run(mod.persist_runtime_preflight_outcome(flags=_flags(session_ledger_enabled=False), preflight=pf, payload_session_id="s1", chat_session_id="s1", user_email="u@e.com", user_id=None, user_request="read status"))
    assert called == {"session": 0, "approval": 0}

    asyncio.run(mod.persist_runtime_preflight_outcome(flags=_flags(session_ledger_enabled=True), preflight=pf, payload_session_id="s1", chat_session_id="s1", user_email="u@e.com", user_id=None, user_request="read status"))
    assert called == {"session": 1, "approval": 0}


def test_blocked_and_unknown_approval_and_receipts(monkeypatch):
    seen = {"approval": [], "updates": []}

    async def fake_create(_):
        return None

    async def fake_update(_session_id, changes):
        seen["updates"].append(changes)

    async def fake_approval(**kwargs):
        seen["approval"].append(kwargs)

    monkeypatch.setattr(mod, "create_agent_session", fake_create)
    monkeypatch.setattr(mod, "update_agent_session", fake_update)
    monkeypatch.setattr(mod, "create_approval_item", fake_approval)

    blocked = AgentPreflightResult(allow_execute=False, requires_approval=True, is_side_effect=True, classification_known=True, receipt_fragment={"output_summary": "email_send", "detail": "token=mysecrettoken"})
    asyncio.run(mod.persist_runtime_preflight_outcome(flags=_flags(approval_persistence_enabled=True, runtime_receipts_enabled=True), preflight=blocked, payload_session_id="s2", chat_session_id="s2", user_email="u@e.com", user_id=None, user_request="send email token=mysecrettoken"))
    assert len(seen["approval"]) == 1
    assert seen["approval"][0]["action_type"] == "email_send"
    assert "mysecrettoken" not in str(seen["updates"][0])

    unknown = AgentPreflightResult(allow_execute=False, requires_approval=False, is_side_effect=False, classification_known=False, receipt_fragment={"output_summary": "unknown"})
    asyncio.run(mod.persist_runtime_preflight_outcome(flags=_flags(approval_persistence_enabled=True), preflight=unknown, payload_session_id="s3", chat_session_id="s3", user_email="u@e.com", user_id=None, user_request="blorb glorb"))
    assert len(seen["approval"]) == 2
    assert seen["approval"][1]["action_type"] == "unknown"


def test_blocked_approval_persistence_does_not_require_session_ledger(monkeypatch):
    called = {"session": 0, "approval": 0}

    async def fake_create(_):
        called["session"] += 1

    async def fake_approval(**_):
        called["approval"] += 1

    monkeypatch.setattr(mod, "create_agent_session", fake_create)
    monkeypatch.setattr(mod, "create_approval_item", fake_approval)

    blocked = AgentPreflightResult(allow_execute=False, requires_approval=True, is_side_effect=True, classification_known=True, receipt_fragment={"output_summary": "send_email"})
    asyncio.run(mod.persist_runtime_preflight_outcome(flags=_flags(session_ledger_enabled=False, approval_persistence_enabled=True), preflight=blocked, payload_session_id="s4", chat_session_id="s4", user_email="u@e.com", user_id=None, user_request="send email"))
    assert called == {"session": 0, "approval": 1}


def test_preflight_exception_best_effort_redacted(monkeypatch):
    seen = {"session": None, "updates": []}

    async def fake_create(record):
        seen["session"] = record.model_dump()

    async def fake_update(_session_id, changes):
        seen["updates"].append(changes)

    monkeypatch.setattr(mod, "create_agent_session", fake_create)
    monkeypatch.setattr(mod, "update_agent_session", fake_update)
    asyncio.run(mod.persist_runtime_preflight_error(flags=_flags(runtime_receipts_enabled=True), payload_session_id="e1", chat_session_id="e1", user_email="u@e.com", user_id=None, user_request="check", error_detail="Authorization: Bearer secret-token"))
    assert seen["session"]["status"] == "error"
    assert "secret-token" not in str(seen["session"])
    assert "secret-token" not in str(seen["updates"])
