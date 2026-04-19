"""
Test suite for Memory Profile CRUD endpoints:
- GET /api/caos/memory - List profile memories with optional bin_name filter
- POST /api/caos/memory/save - Save personal_facts and general memories
- PATCH /api/caos/memory/{memory_id} - Edit content and move memories between bins
- DELETE /api/caos/memory/{memory_id} - Remove memory entries
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
TEST_USER_EMAIL = "michael@example.com"


class TestMemoryListEndpoint:
    """Tests for GET /api/caos/memory"""

    def test_list_memories_returns_200(self):
        """List memories should return 200 status"""
        response = requests.get(
            f"{BASE_URL}/api/caos/memory",
            params={"user_email": TEST_USER_EMAIL}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ List memories returned {len(data)} entries")

    def test_list_memories_filter_by_bin_name(self):
        """List memories with bin_name filter should return filtered results"""
        # First, save a personal fact to ensure we have data
        save_response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": f"TEST_filter_fact_{uuid.uuid4().hex[:8]}",
                "bin_name": "personal_facts"
            }
        )
        assert save_response.status_code == 200, f"Save failed: {save_response.text}"
        
        # Now filter by personal_facts
        response = requests.get(
            f"{BASE_URL}/api/caos/memory",
            params={"user_email": TEST_USER_EMAIL, "bin_name": "personal_facts"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # All returned memories should have bin_name = personal_facts
        for memory in data:
            assert memory.get("bin_name") == "personal_facts", f"Expected bin_name=personal_facts, got {memory.get('bin_name')}"
        print(f"✓ Filter by bin_name=personal_facts returned {len(data)} entries")

    def test_list_memories_filter_by_general_bin(self):
        """List memories with bin_name=general filter"""
        response = requests.get(
            f"{BASE_URL}/api/caos/memory",
            params={"user_email": TEST_USER_EMAIL, "bin_name": "general"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        for memory in data:
            assert memory.get("bin_name") == "general", f"Expected bin_name=general, got {memory.get('bin_name')}"
        print(f"✓ Filter by bin_name=general returned {len(data)} entries")


class TestMemorySaveEndpoint:
    """Tests for POST /api/caos/memory/save"""

    def test_save_personal_fact(self):
        """Save a personal fact memory"""
        unique_content = f"TEST_personal_fact_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": unique_content,
                "bin_name": "personal_facts"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "id" in data, "Response should contain id"
        assert data.get("content") == unique_content, f"Content mismatch: {data.get('content')}"
        assert data.get("bin_name") == "personal_facts", f"bin_name mismatch: {data.get('bin_name')}"
        assert data.get("source") == "user_saved", f"source should be user_saved, got {data.get('source')}"
        assert "created_at" in data, "Response should contain created_at"
        assert "updated_at" in data, "Response should contain updated_at"
        
        print(f"✓ Saved personal fact with id={data['id']}")
        return data["id"]

    def test_save_general_memory(self):
        """Save a general memory"""
        unique_content = f"TEST_general_memory_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": unique_content,
                "bin_name": "general"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("content") == unique_content
        assert data.get("bin_name") == "general"
        print(f"✓ Saved general memory with id={data['id']}")
        return data["id"]

    def test_save_memory_with_tags(self):
        """Save memory with custom tags"""
        unique_content = f"TEST_tagged_memory_{uuid.uuid4().hex[:8]}"
        custom_tags = ["work", "project", "deadline"]
        response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": unique_content,
                "bin_name": "general",
                "tags": custom_tags
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("tags") == custom_tags, f"Tags mismatch: {data.get('tags')}"
        print(f"✓ Saved memory with custom tags: {custom_tags}")
        return data["id"]

    def test_save_memory_with_priority(self):
        """Save memory with custom priority"""
        unique_content = f"TEST_priority_memory_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": unique_content,
                "bin_name": "general",
                "priority": 80
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("priority") == 80, f"Priority mismatch: {data.get('priority')}"
        print(f"✓ Saved memory with priority=80")
        return data["id"]

    def test_save_memory_persists_in_list(self):
        """Verify saved memory appears in list endpoint"""
        unique_content = f"TEST_persist_check_{uuid.uuid4().hex[:8]}"
        
        # Save memory
        save_response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": unique_content,
                "bin_name": "personal_facts"
            }
        )
        assert save_response.status_code == 200
        saved_id = save_response.json()["id"]
        
        # Verify it appears in list
        list_response = requests.get(
            f"{BASE_URL}/api/caos/memory",
            params={"user_email": TEST_USER_EMAIL}
        )
        assert list_response.status_code == 200
        memories = list_response.json()
        
        found = any(m.get("id") == saved_id for m in memories)
        assert found, f"Saved memory {saved_id} not found in list"
        print(f"✓ Verified memory {saved_id} persists in list")


class TestMemoryUpdateEndpoint:
    """Tests for PATCH /api/caos/memory/{memory_id}"""

    def test_update_memory_content(self):
        """Update memory content"""
        # First create a memory
        original_content = f"TEST_original_{uuid.uuid4().hex[:8]}"
        save_response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": original_content,
                "bin_name": "general"
            }
        )
        assert save_response.status_code == 200
        memory_id = save_response.json()["id"]
        
        # Update content
        updated_content = f"TEST_updated_{uuid.uuid4().hex[:8]}"
        update_response = requests.patch(
            f"{BASE_URL}/api/caos/memory/{memory_id}",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": updated_content
            }
        )
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        data = update_response.json()
        
        assert data.get("content") == updated_content, f"Content not updated: {data.get('content')}"
        assert data.get("id") == memory_id, "ID should remain the same"
        print(f"✓ Updated memory content for id={memory_id}")

    def test_move_memory_to_personal_facts(self):
        """Move memory from general to personal_facts bin"""
        # Create a general memory
        content = f"TEST_move_to_facts_{uuid.uuid4().hex[:8]}"
        save_response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": content,
                "bin_name": "general"
            }
        )
        assert save_response.status_code == 200
        memory_id = save_response.json()["id"]
        
        # Move to personal_facts
        update_response = requests.patch(
            f"{BASE_URL}/api/caos/memory/{memory_id}",
            json={
                "user_email": TEST_USER_EMAIL,
                "bin_name": "personal_facts"
            }
        )
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        data = update_response.json()
        
        assert data.get("bin_name") == "personal_facts", f"bin_name not updated: {data.get('bin_name')}"
        print(f"✓ Moved memory {memory_id} to personal_facts bin")

    def test_move_memory_to_general(self):
        """Move memory from personal_facts to general bin"""
        # Create a personal_facts memory
        content = f"TEST_move_to_general_{uuid.uuid4().hex[:8]}"
        save_response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": content,
                "bin_name": "personal_facts"
            }
        )
        assert save_response.status_code == 200
        memory_id = save_response.json()["id"]
        
        # Move to general
        update_response = requests.patch(
            f"{BASE_URL}/api/caos/memory/{memory_id}",
            json={
                "user_email": TEST_USER_EMAIL,
                "bin_name": "general"
            }
        )
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        data = update_response.json()
        
        assert data.get("bin_name") == "general", f"bin_name not updated: {data.get('bin_name')}"
        print(f"✓ Moved memory {memory_id} to general bin")

    def test_update_memory_priority(self):
        """Update memory priority"""
        content = f"TEST_priority_update_{uuid.uuid4().hex[:8]}"
        save_response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": content,
                "bin_name": "general",
                "priority": 50
            }
        )
        assert save_response.status_code == 200
        memory_id = save_response.json()["id"]
        
        # Update priority
        update_response = requests.patch(
            f"{BASE_URL}/api/caos/memory/{memory_id}",
            json={
                "user_email": TEST_USER_EMAIL,
                "priority": 90
            }
        )
        assert update_response.status_code == 200
        data = update_response.json()
        
        assert data.get("priority") == 90, f"Priority not updated: {data.get('priority')}"
        print(f"✓ Updated memory priority to 90")

    def test_update_nonexistent_memory_returns_404(self):
        """Update non-existent memory should return 404"""
        fake_id = str(uuid.uuid4())
        response = requests.patch(
            f"{BASE_URL}/api/caos/memory/{fake_id}",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": "This should fail"
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Update non-existent memory correctly returns 404")

    def test_update_persists_in_list(self):
        """Verify updated memory reflects in list endpoint"""
        content = f"TEST_update_persist_{uuid.uuid4().hex[:8]}"
        save_response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": content,
                "bin_name": "general"
            }
        )
        assert save_response.status_code == 200
        memory_id = save_response.json()["id"]
        
        # Update to personal_facts
        update_response = requests.patch(
            f"{BASE_URL}/api/caos/memory/{memory_id}",
            json={
                "user_email": TEST_USER_EMAIL,
                "bin_name": "personal_facts"
            }
        )
        assert update_response.status_code == 200
        
        # Verify in list with filter
        list_response = requests.get(
            f"{BASE_URL}/api/caos/memory",
            params={"user_email": TEST_USER_EMAIL, "bin_name": "personal_facts"}
        )
        assert list_response.status_code == 200
        memories = list_response.json()
        
        found = any(m.get("id") == memory_id for m in memories)
        assert found, f"Updated memory {memory_id} not found in personal_facts list"
        print(f"✓ Verified updated memory {memory_id} persists with new bin_name")


class TestMemoryDeleteEndpoint:
    """Tests for DELETE /api/caos/memory/{memory_id}"""

    def test_delete_memory(self):
        """Delete a memory entry"""
        # First create a memory
        content = f"TEST_delete_{uuid.uuid4().hex[:8]}"
        save_response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": content,
                "bin_name": "general"
            }
        )
        assert save_response.status_code == 200
        memory_id = save_response.json()["id"]
        
        # Delete the memory
        delete_response = requests.delete(
            f"{BASE_URL}/api/caos/memory/{memory_id}",
            params={"user_email": TEST_USER_EMAIL}
        )
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        data = delete_response.json()
        
        assert data.get("ok") == True, "Response should have ok=True"
        assert data.get("deleted_id") == memory_id, f"deleted_id mismatch: {data.get('deleted_id')}"
        print(f"✓ Deleted memory {memory_id}")

    def test_delete_removes_from_list(self):
        """Verify deleted memory no longer appears in list"""
        content = f"TEST_delete_verify_{uuid.uuid4().hex[:8]}"
        save_response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": content,
                "bin_name": "general"
            }
        )
        assert save_response.status_code == 200
        memory_id = save_response.json()["id"]
        
        # Delete
        delete_response = requests.delete(
            f"{BASE_URL}/api/caos/memory/{memory_id}",
            params={"user_email": TEST_USER_EMAIL}
        )
        assert delete_response.status_code == 200
        
        # Verify not in list
        list_response = requests.get(
            f"{BASE_URL}/api/caos/memory",
            params={"user_email": TEST_USER_EMAIL}
        )
        assert list_response.status_code == 200
        memories = list_response.json()
        
        found = any(m.get("id") == memory_id for m in memories)
        assert not found, f"Deleted memory {memory_id} still appears in list"
        print(f"✓ Verified deleted memory {memory_id} no longer in list")

    def test_delete_nonexistent_memory_returns_404(self):
        """Delete non-existent memory should return 404"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(
            f"{BASE_URL}/api/caos/memory/{fake_id}",
            params={"user_email": TEST_USER_EMAIL}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Delete non-existent memory correctly returns 404")


class TestMemoryEndToEndFlow:
    """End-to-end tests for complete memory CRUD workflow"""

    def test_full_crud_workflow(self):
        """Test complete Create -> Read -> Update -> Delete flow"""
        unique_id = uuid.uuid4().hex[:8]
        
        # CREATE
        create_content = f"TEST_e2e_create_{unique_id}"
        create_response = requests.post(
            f"{BASE_URL}/api/caos/memory/save",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": create_content,
                "bin_name": "general",
                "priority": 50
            }
        )
        assert create_response.status_code == 200, f"CREATE failed: {create_response.text}"
        memory_id = create_response.json()["id"]
        print(f"  CREATE: memory_id={memory_id}")
        
        # READ (verify in list)
        list_response = requests.get(
            f"{BASE_URL}/api/caos/memory",
            params={"user_email": TEST_USER_EMAIL}
        )
        assert list_response.status_code == 200
        memories = list_response.json()
        created_memory = next((m for m in memories if m.get("id") == memory_id), None)
        assert created_memory is not None, "Created memory not found in list"
        assert created_memory.get("content") == create_content
        assert created_memory.get("bin_name") == "general"
        print(f"  READ: verified memory exists with correct content")
        
        # UPDATE (change content and move to personal_facts)
        updated_content = f"TEST_e2e_updated_{unique_id}"
        update_response = requests.patch(
            f"{BASE_URL}/api/caos/memory/{memory_id}",
            json={
                "user_email": TEST_USER_EMAIL,
                "content": updated_content,
                "bin_name": "personal_facts",
                "priority": 80
            }
        )
        assert update_response.status_code == 200, f"UPDATE failed: {update_response.text}"
        updated_data = update_response.json()
        assert updated_data.get("content") == updated_content
        assert updated_data.get("bin_name") == "personal_facts"
        assert updated_data.get("priority") == 80
        print(f"  UPDATE: content, bin_name, and priority updated")
        
        # READ (verify update persisted)
        list_response2 = requests.get(
            f"{BASE_URL}/api/caos/memory",
            params={"user_email": TEST_USER_EMAIL, "bin_name": "personal_facts"}
        )
        assert list_response2.status_code == 200
        memories2 = list_response2.json()
        updated_memory = next((m for m in memories2 if m.get("id") == memory_id), None)
        assert updated_memory is not None, "Updated memory not found in personal_facts list"
        assert updated_memory.get("content") == updated_content
        print(f"  READ: verified update persisted")
        
        # DELETE
        delete_response = requests.delete(
            f"{BASE_URL}/api/caos/memory/{memory_id}",
            params={"user_email": TEST_USER_EMAIL}
        )
        assert delete_response.status_code == 200, f"DELETE failed: {delete_response.text}"
        print(f"  DELETE: memory removed")
        
        # READ (verify deletion)
        list_response3 = requests.get(
            f"{BASE_URL}/api/caos/memory",
            params={"user_email": TEST_USER_EMAIL}
        )
        assert list_response3.status_code == 200
        memories3 = list_response3.json()
        deleted_memory = next((m for m in memories3 if m.get("id") == memory_id), None)
        assert deleted_memory is None, "Deleted memory still appears in list"
        print(f"  READ: verified memory deleted")
        
        print(f"✓ Full CRUD workflow completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
