"""CAOS memory workbench API regression tests for core contract and isolation flows."""

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


# Module: API contract and session isolation boundary
def test_contract_declares_runtime_and_isolation_boundary(api_client):
    response = api_client.get(f"{BASE_URL.rstrip('/')}/api/caos/contract", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["runtime"] == "fastapi-python"
    assert data["isolation_boundary"] == "session_id"
    assert isinstance(data["memory_pipeline"], list)


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
