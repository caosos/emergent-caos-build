"""Tests for token-derived ARC/WCW meter fields in chat response and persisted receipts."""

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
        "email": f"TEST_token_meter_{token}@example.com",
        "title": f"TEST Token Meter {token}",
    }


# Token fields that must be present in chat response receipt
REQUIRED_TOKEN_FIELDS = [
    "active_context_tokens",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "session_total_tokens",
    "token_source",
]

# Additional token breakdown fields
TOKEN_BREAKDOWN_FIELDS = [
    "history_tokens",
    "memory_tokens",
    "continuity_tokens",
    "system_prompt_tokens",
    "user_message_tokens",
    "session_prompt_tokens_total",
    "session_completion_tokens_total",
]


class TestChatTokenMeterFields:
    """Verify POST /api/caos/chat returns token-derived receipt fields for ARC/WCW."""

    def test_chat_response_contains_required_token_fields(self, api_client, test_identity):
        """Chat response receipt must include all required token meter fields."""
        # Setup: create profile and session
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Token User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        # Execute chat turn
        chat_payload = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Test message for token meter verification",
        }
        response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        
        # Retry once if server error
        if response.status_code >= 500:
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        
        assert response.status_code == 200
        data = response.json()
        receipt = data.get("receipt", {})

        # Verify all required token fields are present
        for field in REQUIRED_TOKEN_FIELDS:
            assert field in receipt, f"Missing required token field: {field}"
            
        # Verify token_source is valid
        assert receipt["token_source"] in ["provider_usage", "local_tokenizer_fallback"], \
            f"Invalid token_source: {receipt['token_source']}"

    def test_chat_response_token_values_are_positive_integers(self, api_client, test_identity):
        """Token count fields must be positive integers."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Token User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        chat_payload = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Another test message for token validation",
        }
        response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        if response.status_code >= 500:
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        
        assert response.status_code == 200
        receipt = response.json().get("receipt", {})

        # Verify numeric token fields are integers >= 0
        numeric_fields = [f for f in REQUIRED_TOKEN_FIELDS if f != "token_source"]
        for field in numeric_fields:
            value = receipt.get(field)
            assert isinstance(value, int), f"{field} should be int, got {type(value)}"
            assert value >= 0, f"{field} should be >= 0, got {value}"

        # prompt_tokens and completion_tokens should be > 0 for a real turn
        assert receipt["prompt_tokens"] > 0, "prompt_tokens should be > 0"
        assert receipt["completion_tokens"] > 0, "completion_tokens should be > 0"
        assert receipt["total_tokens"] > 0, "total_tokens should be > 0"

    def test_chat_response_contains_token_breakdown_fields(self, api_client, test_identity):
        """Chat response should include detailed token breakdown fields."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Token User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        chat_payload = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Test for token breakdown fields",
        }
        response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        if response.status_code >= 500:
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        
        assert response.status_code == 200
        receipt = response.json().get("receipt", {})

        # Verify breakdown fields are present
        for field in TOKEN_BREAKDOWN_FIELDS:
            assert field in receipt, f"Missing token breakdown field: {field}"
            assert isinstance(receipt[field], int), f"{field} should be int"


class TestPersistedReceiptTokenFields:
    """Verify GET /api/caos/sessions/{session_id}/artifacts returns receipts with token fields."""

    def test_persisted_receipt_contains_all_token_fields(self, api_client, test_identity):
        """Persisted receipts from artifacts endpoint must include token meter fields."""
        # Setup
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Token User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        # Execute chat to create receipt
        chat_payload = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Test message for persisted receipt verification",
        }
        chat_response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        if chat_response.status_code >= 500:
            chat_response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        assert chat_response.status_code == 200

        # Fetch artifacts
        artifacts_response = api_client.get(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_id}/artifacts", timeout=20
        )
        assert artifacts_response.status_code == 200
        artifacts = artifacts_response.json()
        
        assert len(artifacts["receipts"]) >= 1, "Should have at least one receipt"
        receipt = artifacts["receipts"][0]

        # Verify all required token fields in persisted receipt
        for field in REQUIRED_TOKEN_FIELDS:
            assert field in receipt, f"Persisted receipt missing field: {field}"

        # Verify breakdown fields
        for field in TOKEN_BREAKDOWN_FIELDS:
            assert field in receipt, f"Persisted receipt missing breakdown field: {field}"

    def test_persisted_receipt_token_values_match_response(self, api_client, test_identity):
        """Token values in persisted receipt should be consistent with chat response."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Token User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        chat_payload = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Test for receipt consistency",
        }
        chat_response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        if chat_response.status_code >= 500:
            chat_response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        assert chat_response.status_code == 200
        
        response_receipt = chat_response.json().get("receipt", {})

        # Fetch persisted receipt
        artifacts_response = api_client.get(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_id}/artifacts", timeout=20
        )
        assert artifacts_response.status_code == 200
        persisted_receipt = artifacts_response.json()["receipts"][0]

        # Key token fields should match
        assert persisted_receipt["token_source"] == response_receipt["token_source"]
        assert persisted_receipt["prompt_tokens"] == response_receipt["prompt_tokens"]
        assert persisted_receipt["completion_tokens"] == response_receipt["completion_tokens"]
        assert persisted_receipt["total_tokens"] == response_receipt["total_tokens"]
        assert persisted_receipt["active_context_tokens"] == response_receipt["active_context_tokens"]


class TestSessionTokenAccumulation:
    """Verify session_total_tokens accumulates across multiple turns."""

    def test_session_total_tokens_accumulates_across_turns(self, api_client, test_identity):
        """session_total_tokens should increase with each chat turn."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Token User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        # First turn
        chat_payload_1 = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "First message for accumulation test",
        }
        response_1 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload_1, timeout=60)
        if response_1.status_code >= 500:
            response_1 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload_1, timeout=60)
        assert response_1.status_code == 200
        
        receipt_1 = response_1.json().get("receipt", {})
        session_total_1 = receipt_1.get("session_total_tokens", 0)
        
        # Second turn
        chat_payload_2 = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Second message for accumulation test",
        }
        response_2 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload_2, timeout=60)
        if response_2.status_code >= 500:
            response_2 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload_2, timeout=60)
        assert response_2.status_code == 200
        
        receipt_2 = response_2.json().get("receipt", {})
        session_total_2 = receipt_2.get("session_total_tokens", 0)

        # Session total should have increased
        assert session_total_2 > session_total_1, \
            f"session_total_tokens should increase: {session_total_1} -> {session_total_2}"
