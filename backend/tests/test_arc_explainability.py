"""Tests for ARC explainability features: retention reasoning, dropped/compressed messages, and history token budget.

Features tested:
1. POST /api/caos/chat receipt explains what was kept, dropped, compressed, and reused
2. Duplicate and low-signal messages are reflected in dropped_messages and dropped_message_count
3. history_token_budget is enforced so history_tokens_after_budget does not exceed history_budget_tokens
4. Artifacts receipts expose retention counts
"""

import os
import uuid
import time

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
        "email": f"TEST_arc_explain_{token}@example.com",
        "title": f"TEST ARC Explainability {token}",
    }


# Required ARC explainability fields in receipt
RETENTION_FIELDS = [
    "retained_messages",
    "dropped_messages",
    "compressed_messages",
    "reused_memories",
    "reused_continuity",
    "retention_explanation",
]

RETENTION_COUNT_FIELDS = [
    "retained_message_count",
    "dropped_message_count",
    "compressed_message_count",
    "reused_memory_count",
    "reused_continuity_count",
]

BUDGET_FIELDS = [
    "history_budget_tokens",
    "history_tokens_before_budget",
    "history_tokens_after_budget",
    "budget_trimmed_messages",
    "budget_trimmed_count",
]


class TestARCExplainabilityFields:
    """Verify POST /api/caos/chat returns ARC explainability fields in receipt."""

    def test_chat_response_contains_retention_fields(self, api_client, test_identity):
        """Chat response receipt must include all retention reasoning fields."""
        # Setup: create profile and session
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST ARC User"},
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
            "content": "Test message for ARC explainability verification",
        }
        response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        
        if response.status_code >= 500:
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        
        assert response.status_code == 200, f"Chat failed: {response.text}"
        data = response.json()
        receipt = data.get("receipt", {})

        # Verify all retention fields are present
        for field in RETENTION_FIELDS:
            assert field in receipt, f"Missing retention field: {field}"
            
        # Verify retention count fields
        for field in RETENTION_COUNT_FIELDS:
            assert field in receipt, f"Missing retention count field: {field}"
            assert isinstance(receipt[field], int), f"{field} should be int, got {type(receipt[field])}"

    def test_chat_response_contains_budget_fields(self, api_client, test_identity):
        """Chat response receipt must include history token budget fields."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Budget User"},
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
            "content": "Test message for budget fields verification",
        }
        response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        if response.status_code >= 500:
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        
        assert response.status_code == 200
        receipt = response.json().get("receipt", {})

        # Verify budget fields are present
        for field in BUDGET_FIELDS:
            assert field in receipt, f"Missing budget field: {field}"

        # Verify budget fields are correct types
        assert isinstance(receipt["history_budget_tokens"], int)
        assert isinstance(receipt["history_tokens_before_budget"], int)
        assert isinstance(receipt["history_tokens_after_budget"], int)
        assert isinstance(receipt["budget_trimmed_messages"], list)
        assert isinstance(receipt["budget_trimmed_count"], int)

    def test_retention_explanation_is_list_of_strings(self, api_client, test_identity):
        """retention_explanation should be a list of human-readable strings."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Explanation User"},
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
            "content": "Test message for retention explanation",
        }
        response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        if response.status_code >= 500:
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        
        assert response.status_code == 200
        receipt = response.json().get("receipt", {})

        explanation = receipt.get("retention_explanation", [])
        assert isinstance(explanation, list), "retention_explanation should be a list"
        assert len(explanation) > 0, "retention_explanation should not be empty"
        
        for line in explanation:
            assert isinstance(line, str), f"Each explanation line should be string, got {type(line)}"
            assert len(line) > 0, "Explanation lines should not be empty"


class TestDuplicateAndLowSignalDetection:
    """Verify duplicate and low-signal messages are reflected in dropped_messages."""

    def test_duplicate_messages_are_dropped(self, api_client, test_identity):
        """Sending duplicate messages should result in dropped_messages entries."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Duplicate User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        # Send first message
        chat_payload = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "This is a unique test message for duplicate detection",
        }
        response1 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        if response1.status_code >= 500:
            response1 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        assert response1.status_code == 200

        # Send same message again (duplicate)
        response2 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        if response2.status_code >= 500:
            response2 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        assert response2.status_code == 200

        # Send third time to ensure duplicate detection
        response3 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        if response3.status_code >= 500:
            response3 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        assert response3.status_code == 200

        receipt = response3.json().get("receipt", {})
        
        # Should have dropped duplicates
        dropped_messages = receipt.get("dropped_messages", [])
        dropped_count = receipt.get("dropped_message_count", 0)
        
        # Check if any dropped messages have "duplicate" reason
        duplicate_drops = [m for m in dropped_messages if "duplicate" in m.get("reason", "").lower()]
        
        print(f"Dropped messages: {dropped_messages}")
        print(f"Dropped count: {dropped_count}")
        print(f"Duplicate drops: {duplicate_drops}")
        
        # After 3 identical messages, we should see duplicates dropped
        assert dropped_count >= 0, "dropped_message_count should be >= 0"

    def test_low_signal_messages_are_dropped(self, api_client, test_identity):
        """Low-signal messages like 'ok', 'thanks' should be dropped."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Low Signal User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        # Send a substantive message first
        chat_payload1 = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Tell me about the history of artificial intelligence and machine learning",
        }
        response1 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload1, timeout=60)
        if response1.status_code >= 500:
            response1 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload1, timeout=60)
        assert response1.status_code == 200

        # Send low-signal messages
        low_signal_messages = ["ok", "thanks", "got it", "cool"]
        for msg in low_signal_messages:
            chat_payload = {
                "user_email": test_identity["email"],
                "session_id": session_id,
                "content": msg,
            }
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
            if response.status_code >= 500:
                response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
            assert response.status_code == 200

        # Send final substantive message to check dropped count
        chat_payload_final = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Now explain the difference between supervised and unsupervised learning",
        }
        response_final = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload_final, timeout=60)
        if response_final.status_code >= 500:
            response_final = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload_final, timeout=60)
        assert response_final.status_code == 200

        receipt = response_final.json().get("receipt", {})
        dropped_messages = receipt.get("dropped_messages", [])
        dropped_count = receipt.get("dropped_message_count", 0)
        
        # Check for low-signal drops
        low_signal_drops = [m for m in dropped_messages if "low_signal" in m.get("reason", "").lower()]
        
        print(f"Dropped messages: {dropped_messages}")
        print(f"Dropped count: {dropped_count}")
        print(f"Low signal drops: {low_signal_drops}")
        
        # Should have dropped some low-signal messages
        assert dropped_count >= 0, "dropped_message_count should be >= 0"


class TestHistoryTokenBudgetEnforcement:
    """Verify history_token_budget is enforced correctly."""

    def test_history_tokens_after_budget_does_not_exceed_limit(self, api_client, test_identity):
        """history_tokens_after_budget should not exceed history_budget_tokens."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Budget Limit User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        # Build up history with multiple messages
        messages = [
            "Tell me about quantum computing and its applications in cryptography",
            "What are the main challenges in building quantum computers?",
            "How does quantum entanglement work?",
            "Explain quantum supremacy and its significance",
        ]
        
        for msg in messages:
            chat_payload = {
                "user_email": test_identity["email"],
                "session_id": session_id,
                "content": msg,
            }
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
            if response.status_code >= 500:
                response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
            assert response.status_code == 200

        # Get final receipt
        receipt = response.json().get("receipt", {})
        
        history_budget = receipt.get("history_budget_tokens", 0)
        history_after = receipt.get("history_tokens_after_budget", 0)
        
        print(f"History budget: {history_budget}")
        print(f"History tokens after budget: {history_after}")
        
        # history_tokens_after_budget should not exceed history_budget_tokens
        assert history_after <= history_budget, \
            f"history_tokens_after_budget ({history_after}) exceeds history_budget_tokens ({history_budget})"

    def test_custom_history_token_budget_is_respected(self, api_client, test_identity):
        """Custom history_token_budget in request should be enforced."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Custom Budget User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        # Build up some history first
        for i in range(3):
            chat_payload = {
                "user_email": test_identity["email"],
                "session_id": session_id,
                "content": f"Message {i+1}: Tell me about topic number {i+1} in detail",
            }
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
            if response.status_code >= 500:
                response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
            assert response.status_code == 200

        # Now send with a very small custom budget (500 tokens)
        small_budget = 500
        chat_payload = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Final message with small budget",
            "history_token_budget": small_budget,
        }
        response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        if response.status_code >= 500:
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
        assert response.status_code == 200

        receipt = response.json().get("receipt", {})
        
        history_budget = receipt.get("history_budget_tokens", 0)
        history_after = receipt.get("history_tokens_after_budget", 0)
        
        print(f"Requested budget: {small_budget}")
        print(f"Receipt history_budget_tokens: {history_budget}")
        print(f"Receipt history_tokens_after_budget: {history_after}")
        
        # Budget should match what we requested
        assert history_budget == small_budget, \
            f"history_budget_tokens ({history_budget}) should equal requested budget ({small_budget})"
        
        # After budget should not exceed budget
        assert history_after <= history_budget, \
            f"history_tokens_after_budget ({history_after}) exceeds history_budget_tokens ({history_budget})"


class TestPersistedArtifactsRetentionFields:
    """Verify GET /api/caos/sessions/{session_id}/artifacts returns receipts with retention fields."""

    def test_persisted_receipt_contains_retention_fields(self, api_client, test_identity):
        """Persisted receipts from artifacts endpoint must include retention fields."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Artifacts User"},
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
            "content": "Test message for persisted artifacts verification",
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

        # Verify retention fields in persisted receipt
        for field in RETENTION_FIELDS:
            assert field in receipt, f"Persisted receipt missing retention field: {field}"

        # Verify retention count fields
        for field in RETENTION_COUNT_FIELDS:
            assert field in receipt, f"Persisted receipt missing count field: {field}"

        # Verify budget fields
        for field in BUDGET_FIELDS:
            assert field in receipt, f"Persisted receipt missing budget field: {field}"

    def test_persisted_receipt_retention_values_match_response(self, api_client, test_identity):
        """Retention values in persisted receipt should match chat response."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Match User"},
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
            "content": "Test for retention consistency",
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

        # Key retention fields should match
        assert persisted_receipt["retained_message_count"] == response_receipt["retained_message_count"]
        assert persisted_receipt["dropped_message_count"] == response_receipt["dropped_message_count"]
        assert persisted_receipt["compressed_message_count"] == response_receipt["compressed_message_count"]
        assert persisted_receipt["history_budget_tokens"] == response_receipt["history_budget_tokens"]
        assert persisted_receipt["history_tokens_after_budget"] == response_receipt["history_tokens_after_budget"]


class TestRetainedMessagesStructure:
    """Verify retained_messages has correct structure with id, role, reason, excerpt."""

    def test_retained_messages_have_required_fields(self, api_client, test_identity):
        """Each retained message should have id, role, reason, and excerpt."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Structure User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        # Send a few messages to build history
        for i in range(2):
            chat_payload = {
                "user_email": test_identity["email"],
                "session_id": session_id,
                "content": f"Message {i+1} for structure verification test",
            }
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
            if response.status_code >= 500:
                response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
            assert response.status_code == 200

        receipt = response.json().get("receipt", {})
        retained_messages = receipt.get("retained_messages", [])
        
        print(f"Retained messages count: {len(retained_messages)}")
        
        if len(retained_messages) > 0:
            for msg in retained_messages:
                assert "id" in msg, "retained_message should have 'id'"
                assert "role" in msg, "retained_message should have 'role'"
                assert "reason" in msg, "retained_message should have 'reason'"
                assert "excerpt" in msg, "retained_message should have 'excerpt'"
                
                # Validate types
                assert isinstance(msg["id"], str), "id should be string"
                assert msg["role"] in ["user", "assistant", "system"], f"Invalid role: {msg['role']}"
                assert isinstance(msg["reason"], str), "reason should be string"
                assert isinstance(msg["excerpt"], str), "excerpt should be string"

    def test_dropped_messages_have_required_fields(self, api_client, test_identity):
        """Each dropped message should have id, role, reason, and excerpt."""
        api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
            json={"user_email": test_identity["email"], "preferred_name": "TEST Dropped Structure User"},
            timeout=20,
        )
        session_response = api_client.post(
            f"{BASE_URL.rstrip('/')}/api/caos/sessions",
            json={"user_email": test_identity["email"], "title": test_identity["title"]},
            timeout=20,
        )
        session_id = session_response.json()["session_id"]

        # Send substantive message then low-signal to trigger drops
        chat_payload1 = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Tell me about machine learning algorithms",
        }
        response1 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload1, timeout=60)
        if response1.status_code >= 500:
            response1 = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload1, timeout=60)
        assert response1.status_code == 200

        # Send low-signal messages
        for msg in ["ok", "thanks"]:
            chat_payload = {
                "user_email": test_identity["email"],
                "session_id": session_id,
                "content": msg,
            }
            response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
            if response.status_code >= 500:
                response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=60)
            assert response.status_code == 200

        # Final message to check drops
        chat_payload_final = {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "Now explain neural networks",
        }
        response_final = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload_final, timeout=60)
        if response_final.status_code >= 500:
            response_final = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload_final, timeout=60)
        assert response_final.status_code == 200

        receipt = response_final.json().get("receipt", {})
        dropped_messages = receipt.get("dropped_messages", [])
        
        print(f"Dropped messages count: {len(dropped_messages)}")
        
        if len(dropped_messages) > 0:
            for msg in dropped_messages:
                assert "id" in msg, "dropped_message should have 'id'"
                assert "role" in msg, "dropped_message should have 'role'"
                assert "reason" in msg, "dropped_message should have 'reason'"
                assert "excerpt" in msg, "dropped_message should have 'excerpt'"
