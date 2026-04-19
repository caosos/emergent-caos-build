"""
Test suite for Global Info Bin / Lookup Reuse Cache functionality.
Tests:
- Global info bin population after reusable assistant reply
- Cache reuse on subsequent related chat turns
- Receipt fields: selected_global_cache_ids, global_cache_count, global_cache_tokens, rehydration_order
- GET /api/caos/memory/global-bin endpoint
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
TEST_USER = "michael@example.com"


class TestGlobalInfoBinEndpoint:
    """Tests for GET /api/caos/memory/global-bin endpoint"""

    def test_global_bin_endpoint_returns_200(self):
        """Verify global-bin endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/caos/memory/global-bin", params={"user_email": TEST_USER})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Global bin endpoint returns 200")

    def test_global_bin_response_structure(self):
        """Verify global-bin response has correct structure"""
        response = requests.get(f"{BASE_URL}/api/caos/memory/global-bin", params={"user_email": TEST_USER})
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "user_email" in data, "Response missing user_email field"
        assert "entries" in data, "Response missing entries field"
        assert isinstance(data["entries"], list), "entries should be a list"
        assert data["user_email"] == TEST_USER, f"Expected user_email {TEST_USER}, got {data['user_email']}"
        print(f"PASS: Global bin response structure valid, {len(data['entries'])} entries found")

    def test_global_bin_entry_structure(self):
        """Verify each global bin entry has required fields"""
        response = requests.get(f"{BASE_URL}/api/caos/memory/global-bin", params={"user_email": TEST_USER})
        assert response.status_code == 200
        data = response.json()
        
        if not data["entries"]:
            pytest.skip("No global bin entries to validate structure")
        
        entry = data["entries"][0]
        required_fields = [
            "id", "user_email", "lane", "subject_bins", "retrieval_terms",
            "snippet", "source_session_id", "source_message_id", "hits",
            "created_at", "updated_at"
        ]
        
        for field in required_fields:
            assert field in entry, f"Entry missing required field: {field}"
        
        # Validate types
        assert isinstance(entry["subject_bins"], list), "subject_bins should be a list"
        assert isinstance(entry["retrieval_terms"], list), "retrieval_terms should be a list"
        assert isinstance(entry["snippet"], str), "snippet should be a string"
        assert isinstance(entry["hits"], int), "hits should be an integer"
        print(f"PASS: Global bin entry structure valid - id={entry['id'][:8]}...")

    def test_global_bin_lane_filter(self):
        """Verify global-bin endpoint supports lane filtering"""
        response = requests.get(
            f"{BASE_URL}/api/caos/memory/global-bin",
            params={"user_email": TEST_USER, "lane": "global"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All entries should have the filtered lane
        for entry in data["entries"]:
            assert entry["lane"] == "global", f"Entry has lane {entry['lane']}, expected 'global'"
        print(f"PASS: Lane filter works, {len(data['entries'])} entries with lane='global'")


class TestGlobalBinReceiptFields:
    """Tests for global bin fields in chat receipts"""

    def test_receipt_contains_global_cache_count(self):
        """Verify receipt contains global_cache_count field"""
        # Get existing session with receipts
        sessions_response = requests.get(f"{BASE_URL}/api/caos/sessions", params={"user_email": TEST_USER})
        assert sessions_response.status_code == 200
        sessions = sessions_response.json()
        
        # Find Global Bin Seed session
        global_bin_session = next((s for s in sessions if "Global Bin" in s.get("title", "")), None)
        if not global_bin_session:
            pytest.skip("Global Bin Seed session not found")
        
        artifacts_response = requests.get(f"{BASE_URL}/api/caos/sessions/{global_bin_session['session_id']}/artifacts")
        assert artifacts_response.status_code == 200
        artifacts = artifacts_response.json()
        
        if not artifacts.get("receipts"):
            pytest.skip("No receipts found in Global Bin Seed session")
        
        receipt = artifacts["receipts"][0]
        assert "global_cache_count" in receipt, "Receipt missing global_cache_count field"
        assert isinstance(receipt["global_cache_count"], int), "global_cache_count should be an integer"
        print(f"PASS: Receipt contains global_cache_count={receipt['global_cache_count']}")

    def test_receipt_contains_global_cache_tokens(self):
        """Verify receipt contains global_cache_tokens field"""
        sessions_response = requests.get(f"{BASE_URL}/api/caos/sessions", params={"user_email": TEST_USER})
        sessions = sessions_response.json()
        
        global_bin_session = next((s for s in sessions if "Global Bin" in s.get("title", "")), None)
        if not global_bin_session:
            pytest.skip("Global Bin Seed session not found")
        
        artifacts_response = requests.get(f"{BASE_URL}/api/caos/sessions/{global_bin_session['session_id']}/artifacts")
        artifacts = artifacts_response.json()
        
        if not artifacts.get("receipts"):
            pytest.skip("No receipts found")
        
        receipt = artifacts["receipts"][0]
        assert "global_cache_tokens" in receipt, "Receipt missing global_cache_tokens field"
        assert isinstance(receipt["global_cache_tokens"], int), "global_cache_tokens should be an integer"
        print(f"PASS: Receipt contains global_cache_tokens={receipt['global_cache_tokens']}")

    def test_receipt_contains_selected_global_cache_ids(self):
        """Verify receipt contains selected_global_cache_ids field"""
        sessions_response = requests.get(f"{BASE_URL}/api/caos/sessions", params={"user_email": TEST_USER})
        sessions = sessions_response.json()
        
        global_bin_session = next((s for s in sessions if "Global Bin" in s.get("title", "")), None)
        if not global_bin_session:
            pytest.skip("Global Bin Seed session not found")
        
        artifacts_response = requests.get(f"{BASE_URL}/api/caos/sessions/{global_bin_session['session_id']}/artifacts")
        artifacts = artifacts_response.json()
        
        if not artifacts.get("receipts"):
            pytest.skip("No receipts found")
        
        receipt = artifacts["receipts"][0]
        assert "selected_global_cache_ids" in receipt, "Receipt missing selected_global_cache_ids field"
        assert isinstance(receipt["selected_global_cache_ids"], list), "selected_global_cache_ids should be a list"
        print(f"PASS: Receipt contains selected_global_cache_ids with {len(receipt['selected_global_cache_ids'])} entries")

    def test_receipt_contains_global_bin_status(self):
        """Verify receipt contains global_bin_status field"""
        sessions_response = requests.get(f"{BASE_URL}/api/caos/sessions", params={"user_email": TEST_USER})
        sessions = sessions_response.json()
        
        global_bin_session = next((s for s in sessions if "Global Bin" in s.get("title", "")), None)
        if not global_bin_session:
            pytest.skip("Global Bin Seed session not found")
        
        artifacts_response = requests.get(f"{BASE_URL}/api/caos/sessions/{global_bin_session['session_id']}/artifacts")
        artifacts = artifacts_response.json()
        
        if not artifacts.get("receipts"):
            pytest.skip("No receipts found")
        
        receipt = artifacts["receipts"][0]
        assert "global_bin_status" in receipt, "Receipt missing global_bin_status field"
        assert receipt["global_bin_status"] in ["empty", "reused"], f"Invalid global_bin_status: {receipt['global_bin_status']}"
        print(f"PASS: Receipt contains global_bin_status='{receipt['global_bin_status']}'")

    def test_receipt_rehydration_order_includes_global_bin(self):
        """Verify rehydration_order ends with global_bin_reused or global_bin_empty"""
        sessions_response = requests.get(f"{BASE_URL}/api/caos/sessions", params={"user_email": TEST_USER})
        sessions = sessions_response.json()
        
        global_bin_session = next((s for s in sessions if "Global Bin" in s.get("title", "")), None)
        if not global_bin_session:
            pytest.skip("Global Bin Seed session not found")
        
        artifacts_response = requests.get(f"{BASE_URL}/api/caos/sessions/{global_bin_session['session_id']}/artifacts")
        artifacts = artifacts_response.json()
        
        if not artifacts.get("receipts"):
            pytest.skip("No receipts found")
        
        receipt = artifacts["receipts"][0]
        assert "rehydration_order" in receipt, "Receipt missing rehydration_order field"
        assert isinstance(receipt["rehydration_order"], list), "rehydration_order should be a list"
        
        last_step = receipt["rehydration_order"][-1] if receipt["rehydration_order"] else ""
        assert last_step in ["global_bin_reused", "global_bin_empty"], f"rehydration_order should end with global_bin_*, got: {last_step}"
        print(f"PASS: rehydration_order ends with '{last_step}'")


class TestGlobalBinCacheReuse:
    """Tests for cache reuse behavior on subsequent turns"""

    def test_second_turn_reuses_global_cache(self):
        """Verify second turn receipt shows global_bin_status='reused' when cache is available"""
        sessions_response = requests.get(f"{BASE_URL}/api/caos/sessions", params={"user_email": TEST_USER})
        sessions = sessions_response.json()
        
        global_bin_session = next((s for s in sessions if "Global Bin" in s.get("title", "")), None)
        if not global_bin_session:
            pytest.skip("Global Bin Seed session not found")
        
        artifacts_response = requests.get(f"{BASE_URL}/api/caos/sessions/{global_bin_session['session_id']}/artifacts")
        artifacts = artifacts_response.json()
        
        receipts = artifacts.get("receipts", [])
        if len(receipts) < 2:
            pytest.skip("Need at least 2 receipts to verify cache reuse")
        
        # First receipt (most recent) should show reused status
        latest_receipt = receipts[0]
        assert latest_receipt["global_bin_status"] == "reused", f"Expected 'reused', got '{latest_receipt['global_bin_status']}'"
        assert len(latest_receipt["selected_global_cache_ids"]) > 0, "Expected at least one global cache ID"
        assert latest_receipt["global_cache_count"] > 0, "Expected global_cache_count > 0"
        assert latest_receipt["global_cache_tokens"] > 0, "Expected global_cache_tokens > 0"
        print(f"PASS: Second turn reused global cache - count={latest_receipt['global_cache_count']}, tokens={latest_receipt['global_cache_tokens']}")

    def test_global_cache_ids_match_bin_entries(self):
        """Verify selected_global_cache_ids reference valid entries in global-bin"""
        sessions_response = requests.get(f"{BASE_URL}/api/caos/sessions", params={"user_email": TEST_USER})
        sessions = sessions_response.json()
        
        global_bin_session = next((s for s in sessions if "Global Bin" in s.get("title", "")), None)
        if not global_bin_session:
            pytest.skip("Global Bin Seed session not found")
        
        artifacts_response = requests.get(f"{BASE_URL}/api/caos/sessions/{global_bin_session['session_id']}/artifacts")
        artifacts = artifacts_response.json()
        
        receipts = artifacts.get("receipts", [])
        if not receipts:
            pytest.skip("No receipts found")
        
        latest_receipt = receipts[0]
        selected_ids = latest_receipt.get("selected_global_cache_ids", [])
        
        if not selected_ids:
            pytest.skip("No global cache IDs selected in receipt")
        
        # Get global bin entries
        global_bin_response = requests.get(f"{BASE_URL}/api/caos/memory/global-bin", params={"user_email": TEST_USER})
        global_bin = global_bin_response.json()
        bin_ids = {entry["id"] for entry in global_bin["entries"]}
        
        # Verify all selected IDs exist in global bin
        for cache_id in selected_ids:
            assert cache_id in bin_ids, f"Selected cache ID {cache_id} not found in global bin"
        
        print(f"PASS: All {len(selected_ids)} selected_global_cache_ids found in global-bin")


class TestGlobalBinPopulation:
    """Tests for global bin population after assistant replies"""

    def test_global_bin_has_entries(self):
        """Verify global bin is populated with entries"""
        response = requests.get(f"{BASE_URL}/api/caos/memory/global-bin", params={"user_email": TEST_USER})
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["entries"]) > 0, "Global bin should have at least one entry"
        print(f"PASS: Global bin has {len(data['entries'])} entries")

    def test_global_bin_entry_has_snippet(self):
        """Verify global bin entries have non-empty snippets"""
        response = requests.get(f"{BASE_URL}/api/caos/memory/global-bin", params={"user_email": TEST_USER})
        data = response.json()
        
        if not data["entries"]:
            pytest.skip("No global bin entries")
        
        for entry in data["entries"]:
            assert entry["snippet"], f"Entry {entry['id']} has empty snippet"
            assert len(entry["snippet"]) >= 80, f"Entry snippet too short: {len(entry['snippet'])} chars"
        
        print(f"PASS: All {len(data['entries'])} entries have valid snippets")

    def test_global_bin_entry_has_retrieval_terms(self):
        """Verify global bin entries have retrieval terms"""
        response = requests.get(f"{BASE_URL}/api/caos/memory/global-bin", params={"user_email": TEST_USER})
        data = response.json()
        
        if not data["entries"]:
            pytest.skip("No global bin entries")
        
        for entry in data["entries"]:
            assert entry["retrieval_terms"], f"Entry {entry['id']} has no retrieval terms"
            assert len(entry["retrieval_terms"]) > 0, "retrieval_terms should not be empty"
        
        print(f"PASS: All entries have retrieval terms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
