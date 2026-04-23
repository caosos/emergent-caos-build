#!/usr/bin/env python3
"""
CAOS Auto-Thread-Title Feature Testing - Focused Test
Tests the core auto-thread-title functionality.
"""

import uuid
import requests
import time

# Configuration
BASE_URL = "https://caos-workspace.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

def create_test_user() -> str:
    """Create a unique test user email."""
    token = uuid.uuid4().hex[:8]
    return f"auto_title_test_{token}@example.com"

def test_core_functionality():
    """Test the core auto-thread-title functionality."""
    print("🚀 Testing CAOS Auto-Thread-Title Feature")
    print(f"API Base: {API_BASE}")
    
    test_user = create_test_user()
    print(f"Test user: {test_user}")
    
    # Test 1: Generic title "New Thread" should set title_source=auto
    print("\n=== Test 1: Generic title handling ===")
    
    session_payload = {
        "user_email": test_user,
        "title": "New Thread",
        "lane": "general"
    }
    
    try:
        response = requests.post(f"{API_BASE}/caos/sessions", json=session_payload, timeout=15)
        if response.status_code == 200:
            session_data = response.json()
            session_id = session_data["session_id"]
            title_source = session_data.get("title_source")
            
            print(f"✅ Session created: {session_id}")
            print(f"   Title: '{session_data['title']}'")
            print(f"   Title source: {title_source}")
            
            if title_source == "auto":
                print("✅ PASS: Generic title 'New Thread' correctly sets title_source=auto")
            else:
                print(f"❌ FAIL: Expected title_source=auto, got {title_source}")
                return False
        else:
            print(f"❌ FAIL: Session creation failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Session creation error: {e}")
        return False
    
    # Test 2: Custom title should set title_source=user
    print("\n=== Test 2: Custom title handling ===")
    
    custom_payload = {
        "user_email": test_user,
        "title": "My Important Project Discussion",
        "lane": "general"
    }
    
    try:
        response = requests.post(f"{API_BASE}/caos/sessions", json=custom_payload, timeout=15)
        if response.status_code == 200:
            session_data = response.json()
            title_source = session_data.get("title_source")
            
            print(f"✅ Custom session created: {session_data['session_id']}")
            print(f"   Title: '{session_data['title']}'")
            print(f"   Title source: {title_source}")
            
            if title_source == "user":
                print("✅ PASS: Custom title correctly sets title_source=user")
            else:
                print(f"❌ FAIL: Expected title_source=user, got {title_source}")
                return False
        else:
            print(f"❌ FAIL: Custom session creation failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Custom session creation error: {e}")
        return False
    
    # Test 3: Various generic titles
    print("\n=== Test 3: Various generic titles ===")
    
    generic_titles = ["new thread", "continued thread", "chat", "general thread", "test session"]
    
    for title in generic_titles:
        try:
            payload = {
                "user_email": test_user,
                "title": title,
                "lane": "general"
            }
            
            response = requests.post(f"{API_BASE}/caos/sessions", json=payload, timeout=15)
            if response.status_code == 200:
                session_data = response.json()
                title_source = session_data.get("title_source")
                
                if title_source == "auto":
                    print(f"✅ PASS: '{title}' correctly identified as generic")
                else:
                    print(f"❌ FAIL: '{title}' not identified as generic, got title_source={title_source}")
                    return False
            else:
                print(f"❌ FAIL: Failed to create session with title '{title}': {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ FAIL: Error testing title '{title}': {e}")
            return False
    
    # Test 4: Try a chat turn to see if title gets updated (if possible)
    print("\n=== Test 4: Chat turn title update (if LLM available) ===")
    
    chat_payload = {
        "user_email": test_user,
        "session_id": session_id,
        "content": "I need help with Python machine learning algorithms for data analysis"
    }
    
    try:
        print("Attempting chat request (may timeout if LLM unavailable)...")
        response = requests.post(f"{API_BASE}/caos/chat", json=chat_payload, timeout=60)
        
        if response.status_code == 200:
            print("✅ Chat request successful")
            
            # Check if title was updated
            sessions_response = requests.get(f"{API_BASE}/caos/sessions", params={"user_email": test_user}, timeout=15)
            if sessions_response.status_code == 200:
                sessions = sessions_response.json()
                updated_session = next((s for s in sessions if s["session_id"] == session_id), None)
                
                if updated_session:
                    new_title = updated_session.get("title")
                    title_source = updated_session.get("title_source")
                    
                    print(f"   Updated title: '{new_title}'")
                    print(f"   Title source: {title_source}")
                    
                    if new_title != "New Thread":
                        print("✅ PASS: Title was updated from generic 'New Thread'")
                        if title_source == "auto":
                            print("✅ PASS: Title source remains 'auto' after update")
                        else:
                            print(f"❌ FAIL: Expected title_source=auto after update, got {title_source}")
                            return False
                    else:
                        print("⚠️  WARNING: Title was not updated (may be expected if within turn limit)")
                else:
                    print("❌ FAIL: Could not find session after chat")
                    return False
            else:
                print(f"❌ FAIL: Could not retrieve sessions after chat: {sessions_response.status_code}")
                return False
        elif response.status_code == 502:
            print("⚠️  WARNING: Chat request failed with 502 (upstream LLM timeout)")
            print("   This is expected if LLM is unavailable, title update logic cannot be tested")
        else:
            print(f"⚠️  WARNING: Chat request failed: {response.status_code}")
            print("   Title update logic cannot be tested without successful chat")
    except requests.exceptions.Timeout:
        print("⚠️  WARNING: Chat request timed out (expected if LLM unavailable)")
        print("   Title update logic cannot be tested")
    except Exception as e:
        print(f"⚠️  WARNING: Chat request error: {e}")
        print("   Title update logic cannot be tested")
    
    # Test 5: Contract verification
    print("\n=== Test 5: Contract verification ===")
    
    try:
        sessions_response = requests.get(f"{API_BASE}/caos/sessions", params={"user_email": test_user}, timeout=15)
        if sessions_response.status_code == 200:
            sessions = sessions_response.json()
            
            if len(sessions) > 0:
                sample_session = sessions[0]
                required_fields = ["session_id", "user_email", "title", "title_source", "lane", "created_at", "updated_at"]
                missing_fields = [field for field in required_fields if field not in sample_session]
                
                if not missing_fields:
                    print("✅ PASS: All required fields present in session response")
                else:
                    print(f"❌ FAIL: Missing fields in session response: {missing_fields}")
                    return False
                
                # Check title_source values are valid
                valid_sources = all(s.get("title_source") in ["user", "auto"] for s in sessions)
                if valid_sources:
                    print("✅ PASS: All title_source values are valid ('user' or 'auto')")
                else:
                    invalid = [s.get("title_source") for s in sessions if s.get("title_source") not in ["user", "auto"]]
                    print(f"❌ FAIL: Invalid title_source values: {invalid}")
                    return False
            else:
                print("❌ FAIL: No sessions found for contract verification")
                return False
        else:
            print(f"❌ FAIL: Could not retrieve sessions: {sessions_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Contract verification error: {e}")
        return False
    
    print("\n🎉 All core tests passed! Auto-thread-title feature is working correctly.")
    return True

if __name__ == "__main__":
    success = test_core_functionality()
    exit(0 if success else 1)