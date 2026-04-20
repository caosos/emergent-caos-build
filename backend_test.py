#!/usr/bin/env python3
"""
CAOS Auto-Thread-Title Feature Testing
Tests the new auto-thread-title functionality end-to-end.
"""

import os
import uuid
import requests
import time
from typing import Dict, Any

# Configuration
BASE_URL = "https://memory-hub-63.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

class TestResults:
    def __init__(self):
        self.results = []
        self.errors = []
        
    def add_result(self, test_name: str, passed: bool, details: str = ""):
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        if not passed:
            self.errors.append(f"❌ {test_name}: {details}")
        else:
            print(f"✅ {test_name}: {details}")
    
    def summary(self):
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        print(f"\n=== TEST SUMMARY ===")
        print(f"Passed: {passed}/{total}")
        if self.errors:
            print("\n=== FAILURES ===")
            for error in self.errors:
                print(error)
        return passed == total

def create_test_user() -> str:
    """Create a unique test user email."""
    token = uuid.uuid4().hex[:8]
    return f"auto_title_test_{token}@example.com"

def make_request(method: str, url: str, **kwargs) -> requests.Response:
    """Make HTTP request with timeout and error handling."""
    try:
        # Use longer timeout for chat requests
        timeout = 90 if "/chat" in url else 30
        response = requests.request(method, url, timeout=timeout, **kwargs)
        return response
    except requests.exceptions.Timeout:
        print(f"⚠️  Request timeout for {method} {url}")
        return None
    except Exception as e:
        print(f"⚠️  Request error for {method} {url}: {e}")
        return None

def test_auto_thread_title_feature():
    """Test the complete auto-thread-title feature."""
    results = TestResults()
    
    # Test 0: Basic connectivity check
    print("\n=== Test 0: Basic connectivity ===")
    test_user = create_test_user()
    
    # Test basic session creation first
    basic_session_payload = {
        "user_email": test_user,
        "title": "Connectivity Test",
        "lane": "general"
    }
    
    basic_response = make_request("POST", f"{API_BASE}/caos/sessions", json=basic_session_payload)
    if basic_response and basic_response.status_code == 200:
        results.add_result(
            "Basic API connectivity", 
            True, 
            f"Successfully created session via API"
        )
    else:
        results.add_result(
            "Basic API connectivity", 
            False, 
            f"Failed to connect to API: {basic_response.status_code if basic_response else 'No response'}"
        )
        return results
    
    # Test 1: POST /caos/sessions with generic title sets title_source appropriately
    print("\n=== Test 1: Generic title handling ===")
    
    # Create session with generic title "New Thread"
    session_payload = {
        "user_email": test_user,
        "title": "New Thread",
        "lane": "general"
    }
    
    response = make_request("POST", f"{API_BASE}/caos/sessions", json=session_payload)
    if response and response.status_code == 200:
        session_data = response.json()
        session_id = session_data["session_id"]
        
        # Check title_source is set correctly for generic title
        if session_data.get("title_source") == "auto":
            results.add_result(
                "Generic title sets title_source=auto", 
                True, 
                f"Session created with title_source=auto for 'New Thread'"
            )
        else:
            results.add_result(
                "Generic title sets title_source=auto", 
                False, 
                f"Expected title_source=auto, got {session_data.get('title_source')}"
            )
    else:
        results.add_result(
            "Generic title sets title_source=auto", 
            False, 
            f"Session creation failed: {response.status_code if response else 'No response'} - {response.text if response else 'Timeout'}"
        )
        return results
    
    # Test 2: After chat turn, title should be auto-updated
    print("\n=== Test 2: Auto-title generation after chat ===")
    
    # Send a chat message with descriptive content
    chat_payload = {
        "user_email": test_user,
        "session_id": session_id,
        "content": "I need help with Python machine learning algorithms for data analysis and neural networks"
    }
    
    # Try chat request with retry logic for upstream timeouts
    chat_response = None
    for attempt in range(2):
        print(f"Attempting chat request {attempt + 1}/2...")
        chat_response = make_request("POST", f"{API_BASE}/caos/chat", json=chat_payload)
        
        if chat_response is None:
            print(f"⚠️  Chat attempt {attempt + 1} timed out")
            if attempt == 0:
                time.sleep(3)
                continue
            else:
                # If both attempts timeout, report this but continue with other tests
                results.add_result(
                    "Chat turn successful", 
                    False, 
                    "Chat requests timed out (likely upstream LLM timeout) - title update logic cannot be tested"
                )
                break
        elif chat_response.status_code == 200:
            break
        elif chat_response.status_code >= 500:
            print(f"⚠️  Chat attempt {attempt + 1} failed with {chat_response.status_code}")
            if attempt == 0:
                time.sleep(3)
                continue
        else:
            break
    
    if chat_response and chat_response.status_code == 200:
        chat_data = chat_response.json()
        results.add_result(
            "Chat turn successful", 
            True, 
            f"Chat completed successfully with reply length: {len(chat_data.get('reply', ''))}"
        )
        
        # Check if session title was updated
        sessions_response = make_request("GET", f"{API_BASE}/caos/sessions", params={"user_email": test_user})
        if sessions_response.status_code == 200:
            sessions = sessions_response.json()
            updated_session = next((s for s in sessions if s["session_id"] == session_id), None)
            
            if updated_session:
                new_title = updated_session.get("title")
                title_source = updated_session.get("title_source")
                
                # Check title was updated away from "New Thread"
                if new_title != "New Thread":
                    results.add_result(
                        "Title updated from generic", 
                        True, 
                        f"Title changed from 'New Thread' to '{new_title}'"
                    )
                else:
                    results.add_result(
                        "Title updated from generic", 
                        False, 
                        "Title remained 'New Thread' after chat turn"
                    )
                
                # Check title_source is "auto"
                if title_source == "auto":
                    results.add_result(
                        "Title source set to auto", 
                        True, 
                        f"title_source correctly set to 'auto'"
                    )
                else:
                    results.add_result(
                        "Title source set to auto", 
                        False, 
                        f"Expected title_source='auto', got '{title_source}'"
                    )
            else:
                results.add_result(
                    "Session found after chat", 
                    False, 
                    "Could not find session in sessions list"
                )
        else:
            results.add_result(
                "Get sessions after chat", 
                False, 
                f"Failed to get sessions: {sessions_response.status_code}"
            )
    else:
        error_msg = f"Chat failed: {chat_response.status_code if chat_response else 'No response'}"
        if chat_response:
            error_msg += f" - {chat_response.text}"
        results.add_result("Chat turn successful", False, error_msg)
    
    # Test 3: Custom titles should NOT be overwritten
    print("\n=== Test 3: Custom titles preservation ===")
    
    # Create session with clearly custom title
    custom_session_payload = {
        "user_email": test_user,
        "title": "My Important Project Discussion",
        "lane": "general"
    }
    
    custom_response = make_request("POST", f"{API_BASE}/caos/sessions", json=custom_session_payload)
    if custom_response and custom_response.status_code == 200:
        custom_session_data = custom_response.json()
        custom_session_id = custom_session_data["session_id"]
        
        # Check title_source is "user" for custom title
        if custom_session_data.get("title_source") == "user":
            results.add_result(
                "Custom title sets title_source=user", 
                True, 
                f"Custom title correctly sets title_source=user"
            )
        else:
            results.add_result(
                "Custom title sets title_source=user", 
                False, 
                f"Expected title_source=user, got {custom_session_data.get('title_source')}"
            )
        
        # Send chat message to custom session
        custom_chat_payload = {
            "user_email": test_user,
            "session_id": custom_session_id,
            "content": "Let's discuss database optimization and performance tuning strategies"
        }
        
        custom_chat_response = make_request("POST", f"{API_BASE}/caos/chat", json=custom_chat_payload)
        if custom_chat_response and custom_chat_response.status_code == 200:
            # Check that custom title was NOT changed
            custom_sessions_response = make_request("GET", f"{API_BASE}/caos/sessions", params={"user_email": test_user})
            if custom_sessions_response.status_code == 200:
                custom_sessions = custom_sessions_response.json()
                updated_custom_session = next((s for s in custom_sessions if s["session_id"] == custom_session_id), None)
                
                if updated_custom_session:
                    preserved_title = updated_custom_session.get("title")
                    preserved_title_source = updated_custom_session.get("title_source")
                    
                    if preserved_title == "My Important Project Discussion":
                        results.add_result(
                            "Custom title preserved", 
                            True, 
                            f"Custom title '{preserved_title}' was preserved"
                        )
                    else:
                        results.add_result(
                            "Custom title preserved", 
                            False, 
                            f"Custom title changed from 'My Important Project Discussion' to '{preserved_title}'"
                        )
                    
                    if preserved_title_source == "user":
                        results.add_result(
                            "Custom title_source preserved", 
                            True, 
                            f"title_source remained 'user'"
                        )
                    else:
                        results.add_result(
                            "Custom title_source preserved", 
                            False, 
                            f"title_source changed from 'user' to '{preserved_title_source}'"
                        )
                else:
                    results.add_result(
                        "Custom session found after chat", 
                        False, 
                        "Could not find custom session in sessions list"
                    )
        else:
            if custom_chat_response is None:
                results.add_result(
                    "Custom session chat", 
                    False, 
                    "Chat to custom session timed out"
                )
            else:
                results.add_result(
                    "Custom session chat", 
                    False, 
                    f"Chat to custom session failed: {custom_chat_response.status_code}"
                )
    else:
        results.add_result(
            "Custom session creation", 
            False, 
            f"Custom session creation failed: {custom_response.status_code if custom_response else 'Timeout'}"
        )
    
    # Test 4: Test multiple generic title variations
    print("\n=== Test 4: Various generic titles ===")
    
    generic_titles = ["new thread", "continued thread", "chat", "general thread", "test session"]
    
    for title in generic_titles:
        test_session_payload = {
            "user_email": test_user,
            "title": title,
            "lane": "general"
        }
        
        test_response = make_request("POST", f"{API_BASE}/caos/sessions", json=test_session_payload)
        if test_response.status_code == 200:
            test_session_data = test_response.json()
            if test_session_data.get("title_source") == "auto":
                results.add_result(
                    f"Generic title '{title}' detection", 
                    True, 
                    f"'{title}' correctly identified as generic"
                )
            else:
                results.add_result(
                    f"Generic title '{title}' detection", 
                    False, 
                    f"'{title}' not identified as generic, got title_source={test_session_data.get('title_source')}"
                )
        else:
            results.add_result(
                f"Generic title '{title}' session creation", 
                False, 
                f"Failed to create session with title '{title}'"
            )
    
    # Test 5: Contract regression check - verify session endpoints still work correctly
    print("\n=== Test 5: Contract regression check ===")
    
    # Test GET /caos/sessions still returns all required fields
    final_sessions_response = make_request("GET", f"{API_BASE}/caos/sessions", params={"user_email": test_user})
    if final_sessions_response.status_code == 200:
        final_sessions = final_sessions_response.json()
        
        if len(final_sessions) > 0:
            sample_session = final_sessions[0]
            required_fields = ["session_id", "user_email", "title", "title_source", "lane", "created_at", "updated_at"]
            missing_fields = [field for field in required_fields if field not in sample_session]
            
            if not missing_fields:
                results.add_result(
                    "Session contract fields", 
                    True, 
                    f"All required fields present in session response"
                )
            else:
                results.add_result(
                    "Session contract fields", 
                    False, 
                    f"Missing fields in session response: {missing_fields}"
                )
            
            # Check title_source field values are valid
            valid_title_sources = all(s.get("title_source") in ["user", "auto"] for s in final_sessions)
            if valid_title_sources:
                results.add_result(
                    "Title source values valid", 
                    True, 
                    f"All title_source values are 'user' or 'auto'"
                )
            else:
                invalid_sources = [s.get("title_source") for s in final_sessions if s.get("title_source") not in ["user", "auto"]]
                results.add_result(
                    "Title source values valid", 
                    False, 
                    f"Invalid title_source values found: {invalid_sources}"
                )
        else:
            results.add_result(
                "Sessions exist for contract check", 
                False, 
                "No sessions found for contract verification"
            )
    else:
        results.add_result(
            "Session list endpoint", 
            False, 
            f"GET /caos/sessions failed: {final_sessions_response.status_code}"
        )
    
    # Test 6: Edge case - empty/null title handling
    print("\n=== Test 6: Edge cases ===")
    
    # Test empty title
    empty_title_payload = {
        "user_email": test_user,
        "title": "",
        "lane": "general"
    }
    
    empty_response = make_request("POST", f"{API_BASE}/caos/sessions", json=empty_title_payload)
    if empty_response.status_code == 200:
        empty_session_data = empty_response.json()
        if empty_session_data.get("title_source") == "auto":
            results.add_result(
                "Empty title handling", 
                True, 
                f"Empty title correctly sets title_source=auto"
            )
        else:
            results.add_result(
                "Empty title handling", 
                False, 
                f"Empty title should set title_source=auto, got {empty_session_data.get('title_source')}"
            )
    else:
        results.add_result(
            "Empty title session creation", 
            False, 
            f"Failed to create session with empty title: {empty_response.status_code}"
        )
    
    return results

def main():
    """Run all auto-thread-title tests."""
    print("🚀 Starting CAOS Auto-Thread-Title Feature Tests")
    print(f"Testing against: {BASE_URL}")
    
    try:
        results = test_auto_thread_title_feature()
        success = results.summary()
        
        if success:
            print("\n🎉 All tests passed! Auto-thread-title feature is working correctly.")
        else:
            print(f"\n❌ Some tests failed. Please review the failures above.")
            
        return success
        
    except Exception as e:
        print(f"\n💥 Test execution failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)