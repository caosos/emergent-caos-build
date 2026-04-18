"""CAOS shell API regression tests for session flows, isolation, and chat orchestration."""

import os
import uuid

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="session")
def api_client():
    """Shared HTTP client for CAOS API calls."""
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def test_identity():
    """Unique test identity for creating isolated records per test."""
    token = uuid.uuid4().hex[:8]
    return {
        "email": f"TEST_caos_{token}@example.com",
        "title": f"TEST session {token}",
    }


# Module: user profile upsert flow
def test_profile_upsert_create_and_update(api_client, test_identity):
    create_payload = {
        "user_email": test_identity["email"],
        "preferred_name": "TEST Michael",
    }
    create_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert", json=create_payload, timeout=20
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["user_email"] == test_identity["email"]
    assert created["preferred_name"] == "TEST Michael"
    assert isinstance(created["id"], str)
    assert isinstance(created["structured_memory"], list)

    update_payload = {
        "user_email": test_identity["email"],
        "preferred_name": "TEST Michael Updated",
        "assistant_name": "Aria Prime",
    }
    update_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert", json=update_payload, timeout=20
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["user_email"] == test_identity["email"]
    assert updated["preferred_name"] == "TEST Michael Updated"
    assert updated["assistant_name"] == "Aria Prime"


# Module: sessions and message storage flows
def test_create_session_returns_isolated_session_id(api_client, test_identity):
    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST User"},
        timeout=20,
    )
    response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": test_identity["title"]},
        timeout=20,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["session_id"], str)
    assert data["user_email"] == test_identity["email"]
    assert data["title"] == test_identity["title"]


def test_get_sessions_returns_records_for_user(api_client, test_identity):
    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST User"},
        timeout=20,
    )
    created = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": test_identity["title"]},
        timeout=20,
    )
    assert created.status_code == 200

    list_response = api_client.get(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions", params={"user_email": test_identity["email"]}, timeout=20
    )
    assert list_response.status_code == 200
    sessions = list_response.json()
    assert isinstance(sessions, list)
    assert any(item["session_id"] == created.json()["session_id"] for item in sessions)
    matched = next(item for item in sessions if item["session_id"] == created.json()["session_id"])
    assert matched["user_email"] == test_identity["email"]
    assert matched["title"] == test_identity["title"]


def test_messages_are_scoped_to_their_session_id(api_client, test_identity):
    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST User"},
        timeout=20,
    )
    session_a_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": f"{test_identity['title']} A"},
        timeout=20,
    )
    session_b_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": f"{test_identity['title']} B"},
        timeout=20,
    )
    session_a = session_a_response.json()["session_id"]
    session_b = session_b_response.json()["session_id"]

    message_a_payload = {"session_id": session_a, "role": "user", "content": "TEST session A message"}
    message_b_payload = {"session_id": session_b, "role": "user", "content": "TEST session B message"}
    store_a_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/messages", json=message_a_payload, timeout=20
    )
    store_b_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/messages", json=message_b_payload, timeout=20
    )
    assert store_a_response.status_code == 200
    assert store_b_response.status_code == 200

    get_a_response = api_client.get(f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_a}/messages", timeout=20)
    get_b_response = api_client.get(f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_b}/messages", timeout=20)
    assert get_a_response.status_code == 200
    assert get_b_response.status_code == 200
    messages_a = get_a_response.json()
    messages_b = get_b_response.json()
    assert any(msg["content"] == "TEST session A message" for msg in messages_a)
    assert not any(msg["content"] == "TEST session B message" for msg in messages_a)
    assert any(msg["content"] == "TEST session B message" for msg in messages_b)


def test_get_session_messages_returns_selected_session_history(api_client, test_identity):
    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST User"},
        timeout=20,
    )
    session_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": f"{test_identity['title']} Messages"},
        timeout=20,
    )
    session_id = session_response.json()["session_id"]

    first_message = {"session_id": session_id, "role": "user", "content": "TEST first message in selected thread"}
    second_message = {"session_id": session_id, "role": "assistant", "content": "TEST assistant response in selected thread"}
    first_response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/messages", json=first_message, timeout=20)
    second_response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/messages", json=second_message, timeout=20)
    assert first_response.status_code == 200
    assert second_response.status_code == 200

    list_response = api_client.get(f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_id}/messages", timeout=20)
    assert list_response.status_code == 200
    messages = list_response.json()
    assert isinstance(messages, list)
    assert any(msg["content"] == first_message["content"] and msg["role"] == "user" for msg in messages)
    assert any(msg["content"] == second_message["content"] and msg["role"] == "assistant" for msg in messages)


def test_create_message_returns_404_for_unknown_session(api_client):
    payload = {
        "session_id": "non-existent-session",
        "role": "user",
        "content": "Should fail",
    }
    response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/messages", json=payload, timeout=20)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Session not found"


# Module: structured memory save and context prepare pipeline
def test_memory_save_creates_structured_memory_entry(api_client, test_identity):
    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST User"},
        timeout=20,
    )
    payload = {
        "user_email": test_identity["email"],
        "content": "TEST Atlas payment due Friday for utility bill",
    }
    response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/memory/save", json=payload, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["id"], str)
    assert data["content"] == payload["content"]
    assert isinstance(data["tags"], list)


def test_context_prepare_returns_required_payload_fields(api_client, test_identity):
    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST User"},
        timeout=20,
    )
    session_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": test_identity["title"]},
        timeout=20,
    )
    session_id = session_response.json()["session_id"]

    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/messages",
        json={"session_id": session_id, "role": "user", "content": "Okay"},
        timeout=20,
    )
    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/messages",
        json={"session_id": session_id, "role": "user", "content": "Atlas bill is due Friday"},
        timeout=20,
    )
    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/memory/save",
        json={"user_email": test_identity["email"], "content": "Campaign Atlas is active and urgent"},
        timeout=20,
    )

    prepare_payload = {
        "user_email": test_identity["email"],
        "session_id": session_id,
        "query": "What matters now about Atlas and the bill?",
    }
    response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/context/prepare", json=prepare_payload, timeout=20
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert isinstance(data["sanitized_history"], list)
    assert isinstance(data["injected_memories"], list)
    assert isinstance(data["stats"], dict)
    assert isinstance(data["receipt"], dict)
    assert "retrieval_terms" in data["receipt"]
    assert "reduction_ratio" in data["stats"]


# Module: chat orchestration pipeline (sanitize/retrieval/llm/store receipt)
def test_chat_persists_turn_and_returns_receipt_and_wcw(api_client, test_identity):
    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST User"},
        timeout=20,
    )
    session_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": f"{test_identity['title']} Chat"},
        timeout=20,
    )
    session_id = session_response.json()["session_id"]

    memory_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/memory/save",
        json={
            "user_email": test_identity["email"],
            "content": "TEST remember utility bill due Friday and campaign Atlas active",
        },
        timeout=20,
    )
    assert memory_response.status_code == 200

    chat_payload = {
        "user_email": test_identity["email"],
        "session_id": session_id,
        "content": "What should I prioritize tonight if Atlas and the utility bill matter?",
    }
    first_attempt = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
    response = first_attempt
    if first_attempt.status_code >= 500:
        response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert isinstance(data["reply"], str)
    assert len(data["reply"]) > 0
    assert isinstance(data["receipt"], dict)
    assert isinstance(data["receipt"].get("retrieval_terms"), list)
    assert isinstance(data["wcw_used_estimate"], int)
    assert data["wcw_used_estimate"] >= 1
    assert isinstance(data["wcw_budget"], int)
    assert data["wcw_budget"] > 0

    persisted_messages = api_client.get(f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_id}/messages", timeout=20)
    assert persisted_messages.status_code == 200
    message_history = persisted_messages.json()
    assert any(msg["role"] == "user" and msg["content"] == chat_payload["content"] for msg in message_history)
    assert any(msg["role"] == "assistant" and isinstance(msg["content"], str) and msg["content"] for msg in message_history)


# Module: profile retrieval and session artifact persistence surfaces
def test_get_profile_returns_stored_user_profile(api_client, test_identity):
    upsert_payload = {
        "user_email": test_identity["email"],
        "preferred_name": "TEST Profile Name",
        "assistant_name": "Aria",
        "environment_name": "CAOS",
    }
    upsert_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert", json=upsert_payload, timeout=20
    )
    assert upsert_response.status_code == 200

    get_response = api_client.get(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/{test_identity['email']}", timeout=20
    )
    assert get_response.status_code == 200
    profile = get_response.json()
    assert profile["user_email"] == test_identity["email"]
    assert profile["preferred_name"] == "TEST Profile Name"
    assert profile["assistant_name"] == "Aria"
    assert isinstance(profile["structured_memory"], list)


def test_chat_artifacts_endpoint_returns_receipts_summaries_and_seeds(api_client, test_identity):
    api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST User"},
        timeout=20,
    )
    session_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": f"{test_identity['title']} Artifacts"},
        timeout=20,
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    chat_payload = {
        "user_email": test_identity["email"],
        "session_id": session_id,
        "content": "Summarize this turn and persist receipt summary seed artifacts",
    }
    first_attempt = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
    response = first_attempt
    if first_attempt.status_code >= 500:
        response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
    assert response.status_code == 200

    artifacts_response = api_client.get(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_id}/artifacts", timeout=20
    )
    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()
    assert isinstance(artifacts.get("receipts"), list)
    assert isinstance(artifacts.get("summaries"), list)
    assert isinstance(artifacts.get("seeds"), list)
    assert len(artifacts["receipts"]) >= 1
    assert len(artifacts["summaries"]) >= 1
    assert len(artifacts["seeds"]) >= 1

    first_receipt = artifacts["receipts"][0]
    first_summary = artifacts["summaries"][0]
    first_seed = artifacts["seeds"][0]
    assert first_receipt["session_id"] == session_id
    assert first_summary["session_id"] == session_id
    assert first_seed["session_id"] == session_id
    assert isinstance(first_receipt["retrieval_terms"], list)
    assert isinstance(first_summary["summary"], str)
    assert isinstance(first_seed["topics"], list)
