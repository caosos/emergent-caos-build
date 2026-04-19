"""
Test suite for rehydration order and personal facts receipt fields.
Tests the new receipt contract: rehydration_order, global_bin_status,
selected_personal_fact_ids, selected_general_memory_ids, personal_facts_count, general_memory_count.
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_email():
    """Test user email"""
    return "michael@example.com"


@pytest.fixture(scope="module")
def test_session(api_client, test_user_email):
    """Create a test session for chat tests"""
    response = api_client.post(f"{BASE_URL}/api/caos/sessions", json={
        "user_email": test_user_email,
        "title": f"TEST_rehydration_receipt_{uuid.uuid4().hex[:8]}",
        "lane": "test_rehydration"
    })
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="module")
def personal_fact_memory(api_client, test_user_email):
    """Save a personal fact for testing preferential recall"""
    response = api_client.post(f"{BASE_URL}/api/caos/memory/save", json={
        "user_email": test_user_email,
        "content": "TEST_I prefer thermal checks before all other diagnostics.",
        "bin_name": "personal_facts",
        "tags": ["preference", "diagnostic", "thermal"],
        "priority": 80
    })
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="module")
def general_memory(api_client, test_user_email):
    """Save a general memory for testing separation"""
    response = api_client.post(f"{BASE_URL}/api/caos/memory/save", json={
        "user_email": test_user_email,
        "content": "TEST_The project deadline is next Friday.",
        "bin_name": "general",
        "tags": ["project", "deadline"],
        "priority": 50
    })
    assert response.status_code == 200
    return response.json()


class TestRehydrationOrderReceipt:
    """Tests for rehydration_order and global_bin_status in chat receipt"""

    def test_chat_receipt_contains_rehydration_order(self, api_client, test_user_email, test_session):
        """Verify chat receipt exposes rehydration_order field"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "Hello, what is the current context?"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify receipt exists
        assert "receipt" in data
        receipt = data["receipt"]
        
        # Verify rehydration_order field exists and has expected structure
        assert "rehydration_order" in receipt, "Receipt must contain rehydration_order"
        rehydration_order = receipt["rehydration_order"]
        assert isinstance(rehydration_order, list), "rehydration_order must be a list"
        assert len(rehydration_order) > 0, "rehydration_order must not be empty"
        
        # Verify expected order elements
        expected_elements = ["thread_history", "lane_continuity", "personal_facts", "structured_memory", "global_bin_empty"]
        for element in expected_elements:
            assert element in rehydration_order, f"rehydration_order must contain '{element}'"
        
        print(f"Rehydration order: {rehydration_order}")

    def test_chat_receipt_contains_global_bin_status(self, api_client, test_user_email, test_session):
        """Verify chat receipt exposes global_bin_status field"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "What is the global bin status?"
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        # Verify global_bin_status field exists
        assert "global_bin_status" in receipt, "Receipt must contain global_bin_status"
        global_bin_status = receipt["global_bin_status"]
        assert isinstance(global_bin_status, str), "global_bin_status must be a string"
        assert global_bin_status == "empty", f"Expected global_bin_status='empty', got '{global_bin_status}'"
        
        print(f"Global bin status: {global_bin_status}")


class TestPersonalFactsSeparation:
    """Tests for separation of personal facts from general memories in receipt"""

    def test_receipt_separates_personal_fact_ids(self, api_client, test_user_email, test_session, personal_fact_memory):
        """Verify receipt contains selected_personal_fact_ids separate from general memories"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "What do I prefer for diagnostics?"
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        # Verify selected_personal_fact_ids field exists
        assert "selected_personal_fact_ids" in receipt, "Receipt must contain selected_personal_fact_ids"
        personal_fact_ids = receipt["selected_personal_fact_ids"]
        assert isinstance(personal_fact_ids, list), "selected_personal_fact_ids must be a list"
        
        print(f"Selected personal fact IDs: {personal_fact_ids}")

    def test_receipt_separates_general_memory_ids(self, api_client, test_user_email, test_session, general_memory):
        """Verify receipt contains selected_general_memory_ids separate from personal facts"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "What is the project deadline?"
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        # Verify selected_general_memory_ids field exists
        assert "selected_general_memory_ids" in receipt, "Receipt must contain selected_general_memory_ids"
        general_memory_ids = receipt["selected_general_memory_ids"]
        assert isinstance(general_memory_ids, list), "selected_general_memory_ids must be a list"
        
        print(f"Selected general memory IDs: {general_memory_ids}")

    def test_receipt_contains_personal_facts_count(self, api_client, test_user_email, test_session, personal_fact_memory):
        """Verify receipt contains personal_facts_count field"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "What are my preferences?"
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        # Verify personal_facts_count field exists
        assert "personal_facts_count" in receipt, "Receipt must contain personal_facts_count"
        personal_facts_count = receipt["personal_facts_count"]
        assert isinstance(personal_facts_count, int), "personal_facts_count must be an integer"
        assert personal_facts_count >= 0, "personal_facts_count must be non-negative"
        
        print(f"Personal facts count: {personal_facts_count}")

    def test_receipt_contains_general_memory_count(self, api_client, test_user_email, test_session, general_memory):
        """Verify receipt contains general_memory_count field"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "Tell me about the project."
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        # Verify general_memory_count field exists
        assert "general_memory_count" in receipt, "Receipt must contain general_memory_count"
        general_memory_count = receipt["general_memory_count"]
        assert isinstance(general_memory_count, int), "general_memory_count must be an integer"
        assert general_memory_count >= 0, "general_memory_count must be non-negative"
        
        print(f"General memory count: {general_memory_count}")


class TestPersonalFactsPreferentialRecall:
    """Tests for preferential recall of personal facts for self/preference queries"""

    def test_preference_query_recalls_personal_facts(self, api_client, test_user_email, test_session, personal_fact_memory):
        """Verify personal facts are preferentially recalled for preference queries"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "What do I usually prefer to do first?"
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        # For preference queries, personal facts should be recalled
        personal_fact_ids = receipt.get("selected_personal_fact_ids", [])
        personal_facts_count = receipt.get("personal_facts_count", 0)
        
        # Verify personal facts are being recalled for preference queries
        print(f"Preference query - Personal fact IDs: {personal_fact_ids}, Count: {personal_facts_count}")
        
        # Check injected_memories for personal facts
        injected_memories = data.get("injected_memories", [])
        personal_facts_in_injected = [m for m in injected_memories if m.get("bin_name") == "personal_facts"]
        print(f"Personal facts in injected memories: {len(personal_facts_in_injected)}")

    def test_self_query_recalls_personal_facts(self, api_client, test_user_email, test_session, personal_fact_memory):
        """Verify personal facts are preferentially recalled for self-referential queries"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "What do I always do for diagnostics?"
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        # For self-referential queries, personal facts should be recalled
        personal_fact_ids = receipt.get("selected_personal_fact_ids", [])
        personal_facts_count = receipt.get("personal_facts_count", 0)
        
        print(f"Self query - Personal fact IDs: {personal_fact_ids}, Count: {personal_facts_count}")

    def test_favorite_query_recalls_personal_facts(self, api_client, test_user_email, test_session, personal_fact_memory):
        """Verify personal facts are preferentially recalled for favorite queries"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "What is my favorite diagnostic approach?"
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        personal_fact_ids = receipt.get("selected_personal_fact_ids", [])
        personal_facts_count = receipt.get("personal_facts_count", 0)
        
        print(f"Favorite query - Personal fact IDs: {personal_fact_ids}, Count: {personal_facts_count}")


class TestReceiptFieldsConsistency:
    """Tests for consistency between receipt fields"""

    def test_personal_facts_count_matches_ids_length(self, api_client, test_user_email, test_session, personal_fact_memory):
        """Verify personal_facts_count matches length of selected_personal_fact_ids"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "What are my preferences for thermal checks?"
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        personal_fact_ids = receipt.get("selected_personal_fact_ids", [])
        personal_facts_count = receipt.get("personal_facts_count", 0)
        
        assert personal_facts_count == len(personal_fact_ids), \
            f"personal_facts_count ({personal_facts_count}) must match len(selected_personal_fact_ids) ({len(personal_fact_ids)})"

    def test_general_memory_count_matches_ids_length(self, api_client, test_user_email, test_session, general_memory):
        """Verify general_memory_count matches length of selected_general_memory_ids"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "What is the project deadline?"
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        general_memory_ids = receipt.get("selected_general_memory_ids", [])
        general_memory_count = receipt.get("general_memory_count", 0)
        
        assert general_memory_count == len(general_memory_ids), \
            f"general_memory_count ({general_memory_count}) must match len(selected_general_memory_ids) ({len(general_memory_ids)})"

    def test_total_memory_ids_equals_sum_of_personal_and_general(self, api_client, test_user_email, test_session, personal_fact_memory, general_memory):
        """Verify selected_memory_ids equals personal + general memory IDs"""
        response = api_client.post(f"{BASE_URL}/api/caos/chat", json={
            "user_email": test_user_email,
            "session_id": test_session["session_id"],
            "content": "What do I prefer and what is the deadline?"
        })
        assert response.status_code == 200
        data = response.json()
        
        receipt = data["receipt"]
        
        selected_memory_ids = receipt.get("selected_memory_ids", [])
        personal_fact_ids = receipt.get("selected_personal_fact_ids", [])
        general_memory_ids = receipt.get("selected_general_memory_ids", [])
        
        # All memory IDs should be the union of personal and general
        combined_ids = set(personal_fact_ids) | set(general_memory_ids)
        selected_ids_set = set(selected_memory_ids)
        
        assert combined_ids == selected_ids_set, \
            f"selected_memory_ids should equal union of personal and general IDs"
        
        print(f"Total memories: {len(selected_memory_ids)}, Personal: {len(personal_fact_ids)}, General: {len(general_memory_ids)}")


class TestCleanup:
    """Cleanup test data"""

    def test_cleanup_test_memories(self, api_client, test_user_email):
        """Clean up TEST_ prefixed memories"""
        # List all memories
        response = api_client.get(f"{BASE_URL}/api/caos/memory?user_email={test_user_email}")
        if response.status_code == 200:
            memories = response.json()
            for memory in memories:
                if memory.get("content", "").startswith("TEST_"):
                    delete_response = api_client.delete(
                        f"{BASE_URL}/api/caos/memory/{memory['id']}?user_email={test_user_email}"
                    )
                    print(f"Deleted test memory: {memory['id']}")
