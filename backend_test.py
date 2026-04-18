#!/usr/bin/env python3
"""
CAOS Backend Phase 2A Lane-Aware Memory Testing
Tests the lane-aware memory implementation as specified in the review request.
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List

import aiohttp


# Configuration
BACKEND_URL = "https://deno-env-review.preview.emergentagent.com/api"
TEST_USER_EMAIL = "lane-test-user-phase2a@example.com"
TEST_USER_EMAIL_2 = "lane-test-user-2-phase2a@example.com"


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def assert_true(self, condition: bool, message: str):
        if condition:
            self.passed += 1
            print(f"✅ {message}")
        else:
            self.failed += 1
            self.errors.append(message)
            print(f"❌ {message}")
            
    def assert_equal(self, actual: Any, expected: Any, message: str):
        if actual == expected:
            self.passed += 1
            print(f"✅ {message}")
        else:
            self.failed += 1
            error_msg = f"{message} - Expected: {expected}, Got: {actual}"
            self.errors.append(error_msg)
            print(f"❌ {error_msg}")
            
    def assert_in(self, item: Any, container: Any, message: str):
        if item in container:
            self.passed += 1
            print(f"✅ {message}")
        else:
            self.failed += 1
            error_msg = f"{message} - {item} not found in {container}"
            self.errors.append(error_msg)
            print(f"❌ {error_msg}")
            
    def assert_not_none(self, value: Any, message: str):
        if value is not None:
            self.passed += 1
            print(f"✅ {message}")
        else:
            self.failed += 1
            self.errors.append(message)
            print(f"❌ {message}")
            
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 Test Summary: {self.passed}/{total} passed")
        if self.errors:
            print("\n🔍 Failed Tests:")
            for error in self.errors:
                print(f"  - {error}")
        return self.failed == 0


async def make_request(session: aiohttp.ClientSession, method: str, endpoint: str, data: Dict = None, json_data: Dict = None) -> Dict:
    """Make HTTP request and return JSON response"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        async with session.request(method, url, json=json_data, data=data) as response:
            if response.status >= 400:
                text = await response.text()
                print(f"❌ HTTP {response.status} for {method} {endpoint}: {text}")
                return {"error": f"HTTP {response.status}", "detail": text}
            return await response.json()
    except Exception as e:
        print(f"❌ Request failed for {method} {endpoint}: {e}")
        return {"error": "request_failed", "detail": str(e)}


async def test_session_lane_field(session: aiohttp.ClientSession, result: TestResult):
    """Test 1: POST /caos/sessions accepts/returns a `lane` field (default general if omitted)"""
    print("\n🧪 Test 1: Session lane field handling")
    
    # Test session creation with explicit lane
    session_data = {
        "user_email": TEST_USER_EMAIL,
        "title": "Machine Learning Discussion",
        "lane": "ml"
    }
    response = await make_request(session, "POST", "/caos/sessions", json_data=session_data)
    result.assert_true("error" not in response, "Session creation with explicit lane should succeed")
    result.assert_equal(response.get("lane"), "ml", "Session should return specified lane")
    session_id_1 = response.get("session_id")
    
    # Test session creation without lane (should default to general)
    session_data_no_lane = {
        "user_email": TEST_USER_EMAIL,
        "title": "General Chat"
    }
    response = await make_request(session, "POST", "/caos/sessions", json_data=session_data_no_lane)
    result.assert_true("error" not in response, "Session creation without lane should succeed")
    result.assert_equal(response.get("lane"), "general", "Session should default to 'general' lane when omitted")
    session_id_2 = response.get("session_id")
    
    return session_id_1, session_id_2


async def test_chat_lane_derivation(session: aiohttp.ClientSession, result: TestResult, session_id: str):
    """Test 2: A first chat turn in a new session derives and persists a lane on the session"""
    print("\n🧪 Test 2: Chat turn lane derivation and persistence")
    
    # Send first chat message about machine learning
    chat_data = {
        "user_email": TEST_USER_EMAIL,
        "session_id": session_id,
        "content": "I want to discuss neural networks and deep learning algorithms for computer vision tasks."
    }
    response = await make_request(session, "POST", "/caos/chat", json_data=chat_data)
    result.assert_true("error" not in response, "Chat request should succeed")
    result.assert_not_none(response.get("lane"), "Chat response should include lane field")
    
    # Verify lane is derived from content (should be related to ML/neural networks)
    chat_lane = response.get("lane")
    result.assert_true(chat_lane != "general", f"Lane should be derived from content, not general. Got: {chat_lane}")
    
    # Verify session is updated with the derived lane
    sessions_response = await make_request(session, "GET", f"/caos/sessions?user_email={TEST_USER_EMAIL}")
    result.assert_true("error" not in sessions_response, "Sessions list should be retrievable")
    
    # Find our session and check its lane
    target_session = None
    for sess in sessions_response:
        if sess.get("session_id") == session_id:
            target_session = sess
            break
    
    result.assert_not_none(target_session, "Session should be found in sessions list")
    if target_session:
        result.assert_equal(target_session.get("lane"), chat_lane, "Session lane should be updated to match chat-derived lane")
    
    return chat_lane


async def test_memory_workers_rebuild(session: aiohttp.ClientSession, result: TestResult):
    """Test 3: POST /caos/memory/workers/{user_email}/rebuild returns lane worker records"""
    print("\n🧪 Test 3: Memory workers rebuild endpoint")
    
    response = await make_request(session, "POST", f"/caos/memory/workers/{TEST_USER_EMAIL}/rebuild")
    result.assert_true("error" not in response, "Memory workers rebuild should succeed")
    result.assert_equal(response.get("user_email"), TEST_USER_EMAIL, "Response should include correct user_email")
    result.assert_not_none(response.get("workers"), "Response should include workers array")
    
    workers = response.get("workers", [])
    result.assert_true(len(workers) > 0, "Should return at least one worker record")
    
    # Verify worker record structure
    if workers:
        worker = workers[0]
        required_fields = ["id", "user_email", "lane", "subject_bins", "summary_text", "source_session_ids"]
        for field in required_fields:
            result.assert_not_none(worker.get(field), f"Worker should have {field} field")
    
    return workers


async def test_memory_workers_get(session: aiohttp.ClientSession, result: TestResult):
    """Test 4: GET /caos/memory/workers/{user_email} returns worker records with required fields"""
    print("\n🧪 Test 4: Memory workers get endpoint")
    
    response = await make_request(session, "GET", f"/caos/memory/workers/{TEST_USER_EMAIL}")
    result.assert_true("error" not in response, "Memory workers get should succeed")
    result.assert_equal(response.get("user_email"), TEST_USER_EMAIL, "Response should include correct user_email")
    result.assert_not_none(response.get("workers"), "Response should include workers array")
    
    workers = response.get("workers", [])
    result.assert_true(len(workers) > 0, "Should return at least one worker record")
    
    # Verify all required fields are present
    if workers:
        worker = workers[0]
        required_fields = ["lane", "subject_bins", "summary_text", "source_session_ids"]
        for field in required_fields:
            result.assert_not_none(worker.get(field), f"Worker should have {field} field")
            
        # Verify field types
        result.assert_true(isinstance(worker.get("subject_bins", []), list), "subject_bins should be a list")
        result.assert_true(isinstance(worker.get("source_session_ids", []), list), "source_session_ids should be a list")
        result.assert_true(isinstance(worker.get("summary_text", ""), str), "summary_text should be a string")
    
    return workers


async def test_cross_thread_retrieval(session: aiohttp.ClientSession, result: TestResult):
    """Test 5: Cross-thread retrieval works with continuity from prior summaries/seeds/workers"""
    print("\n🧪 Test 5: Cross-thread retrieval and continuity")
    
    # Create first session and chat about a specific topic
    session_1_data = {
        "user_email": TEST_USER_EMAIL_2,
        "title": "Python Programming Discussion",
        "lane": "programming"
    }
    session_1_response = await make_request(session, "POST", "/caos/sessions", json_data=session_1_data)
    result.assert_true("error" not in session_1_response, "First session creation should succeed")
    session_1_id = session_1_response.get("session_id")
    
    # Chat in first session about Python
    chat_1_data = {
        "user_email": TEST_USER_EMAIL_2,
        "session_id": session_1_id,
        "content": "I'm working on a Python project using FastAPI and need help with async database operations and connection pooling."
    }
    chat_1_response = await make_request(session, "POST", "/caos/chat", json_data=chat_1_data)
    result.assert_true("error" not in chat_1_response, "First chat should succeed")
    
    # Wait a moment for processing
    await asyncio.sleep(2)
    
    # Create second session for the same user
    session_2_data = {
        "user_email": TEST_USER_EMAIL_2,
        "title": "FastAPI Database Help",
        "lane": "programming"
    }
    session_2_response = await make_request(session, "POST", "/caos/sessions", json_data=session_2_data)
    result.assert_true("error" not in session_2_response, "Second session creation should succeed")
    session_2_id = session_2_response.get("session_id")
    
    # Chat in second session about related topic
    chat_2_data = {
        "user_email": TEST_USER_EMAIL_2,
        "session_id": session_2_id,
        "content": "Can you help me optimize my FastAPI database queries? I'm having performance issues."
    }
    chat_2_response = await make_request(session, "POST", "/caos/chat", json_data=chat_2_data)
    result.assert_true("error" not in chat_2_response, "Second chat should succeed")
    
    # Verify continuity fields in response
    receipt = chat_2_response.get("receipt", {})
    required_receipt_fields = [
        "selected_summary_ids", "selected_seed_ids", "selected_worker_ids", 
        "lane", "continuity_chars", "estimated_context_chars"
    ]
    
    for field in required_receipt_fields:
        result.assert_not_none(receipt.get(field), f"Chat receipt should include {field}")
    
    # Verify lane consistency
    result.assert_equal(chat_2_response.get("lane"), "programming", "Second chat should maintain programming lane")
    result.assert_equal(receipt.get("lane"), "programming", "Receipt lane should match chat lane")
    
    # Verify continuity is working (should have some selected items)
    selected_summaries = receipt.get("selected_summary_ids", [])
    selected_seeds = receipt.get("selected_seed_ids", [])
    selected_workers = receipt.get("selected_worker_ids", [])
    
    total_continuity_items = len(selected_summaries) + len(selected_seeds) + len(selected_workers)
    result.assert_true(total_continuity_items > 0, "Should have some continuity items selected from prior sessions")
    
    # Verify continuity chars is reasonable
    continuity_chars = receipt.get("continuity_chars", 0)
    result.assert_true(continuity_chars > 0, "Should have some continuity characters")
    
    return session_1_id, session_2_id


async def test_no_500_errors(session: aiohttp.ClientSession, result: TestResult):
    """Test 6: No 500s or contract mismatches"""
    print("\n🧪 Test 6: Error handling and contract compliance")
    
    # Test various edge cases that should not cause 500 errors
    
    # Test with non-existent user
    response = await make_request(session, "GET", f"/caos/memory/workers/nonexistent@example.com")
    result.assert_true(response.get("error") != "HTTP 500", "Non-existent user should not cause 500 error")
    
    # Test rebuild for non-existent user
    response = await make_request(session, "POST", f"/caos/memory/workers/nonexistent@example.com/rebuild")
    result.assert_true(response.get("error") != "HTTP 500", "Rebuild for non-existent user should not cause 500 error")
    
    # Test chat with invalid session
    chat_data = {
        "user_email": TEST_USER_EMAIL,
        "session_id": "invalid-session-id",
        "content": "Test message"
    }
    response = await make_request(session, "POST", "/caos/chat", json_data=chat_data)
    result.assert_true(response.get("error") != "HTTP 500", "Chat with invalid session should not cause 500 error")
    
    # Test session creation with missing fields
    response = await make_request(session, "POST", "/caos/sessions", json_data={})
    result.assert_true(response.get("error") != "HTTP 500", "Session creation with missing fields should not cause 500 error")


async def run_all_tests():
    """Run all Phase 2A lane-aware memory tests"""
    print("🚀 Starting CAOS Backend Phase 2A Lane-Aware Memory Tests")
    print(f"🎯 Testing against: {BACKEND_URL}")
    
    result = TestResult()
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test 1: Session lane field handling
            session_id_1, session_id_2 = await test_session_lane_field(session, result)
            
            # Test 2: Chat lane derivation (using session with explicit lane)
            if session_id_1:
                derived_lane = await test_chat_lane_derivation(session, result, session_id_1)
            
            # Test 3: Memory workers rebuild
            workers_rebuild = await test_memory_workers_rebuild(session, result)
            
            # Test 4: Memory workers get
            workers_get = await test_memory_workers_get(session, result)
            
            # Test 5: Cross-thread retrieval
            cross_thread_sessions = await test_cross_thread_retrieval(session, result)
            
            # Test 6: Error handling
            await test_no_500_errors(session, result)
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            result.errors.append(f"Test execution failed: {e}")
            result.failed += 1
    
    return result.summary()


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)