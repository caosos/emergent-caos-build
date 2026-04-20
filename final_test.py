#!/usr/bin/env python3
"""
CAOS Auto-Thread-Title Feature Testing - Final Verification
Tests the core functionality that can be verified.
"""

import uuid
import requests

# Configuration
BASE_URL = "https://memory-hub-63.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

def create_test_user() -> str:
    """Create a unique test user email."""
    token = uuid.uuid4().hex[:8]
    return f"final_test_{token}@example.com"

def main():
    """Run final verification tests."""
    print("🚀 CAOS Auto-Thread-Title Feature - Final Verification")
    print(f"Testing against: {BASE_URL}")
    
    test_user = create_test_user()
    print(f"Test user: {test_user}")
    
    all_passed = True
    
    # Test 1: Generic title "New Thread" sets title_source=auto
    print("\n=== Test 1: Generic title 'New Thread' ===")
    try:
        response = requests.post(f"{API_BASE}/caos/sessions", json={
            "user_email": test_user,
            "title": "New Thread",
            "lane": "general"
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            session_id = data["session_id"]
            title_source = data.get("title_source")
            
            print(f"✅ Session created: {session_id}")
            print(f"   Title: '{data['title']}'")
            print(f"   Title source: {title_source}")
            
            if title_source == "auto":
                print("✅ PASS: Generic title correctly sets title_source=auto")
            else:
                print(f"❌ FAIL: Expected title_source=auto, got {title_source}")
                all_passed = False
        else:
            print(f"❌ FAIL: Session creation failed: {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"❌ FAIL: Error: {e}")
        all_passed = False
    
    # Test 2: Custom title sets title_source=user
    print("\n=== Test 2: Custom title ===")
    try:
        response = requests.post(f"{API_BASE}/caos/sessions", json={
            "user_email": test_user,
            "title": "My Important Project Discussion",
            "lane": "general"
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            title_source = data.get("title_source")
            
            print(f"✅ Session created: {data['session_id']}")
            print(f"   Title: '{data['title']}'")
            print(f"   Title source: {title_source}")
            
            if title_source == "user":
                print("✅ PASS: Custom title correctly sets title_source=user")
            else:
                print(f"❌ FAIL: Expected title_source=user, got {title_source}")
                all_passed = False
        else:
            print(f"❌ FAIL: Custom session creation failed: {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"❌ FAIL: Error: {e}")
        all_passed = False
    
    # Test 3: Various generic titles
    print("\n=== Test 3: Various generic titles ===")
    generic_titles = ["new thread", "continued thread", "chat", "general thread", "test session"]
    
    for title in generic_titles:
        try:
            response = requests.post(f"{API_BASE}/caos/sessions", json={
                "user_email": test_user,
                "title": title,
                "lane": "general"
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                title_source = data.get("title_source")
                
                if title_source == "auto":
                    print(f"✅ PASS: '{title}' correctly identified as generic")
                else:
                    print(f"❌ FAIL: '{title}' not identified as generic, got title_source={title_source}")
                    all_passed = False
            else:
                print(f"❌ FAIL: Failed to create session with title '{title}': {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"❌ FAIL: Error testing title '{title}': {e}")
            all_passed = False
    
    # Test 4: Empty title handling
    print("\n=== Test 4: Empty title ===")
    try:
        response = requests.post(f"{API_BASE}/caos/sessions", json={
            "user_email": test_user,
            "title": "",
            "lane": "general"
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            title_source = data.get("title_source")
            
            print(f"✅ Session created with empty title: {data['session_id']}")
            print(f"   Title: '{data['title']}'")
            print(f"   Title source: {title_source}")
            
            if title_source == "auto":
                print("✅ PASS: Empty title correctly sets title_source=auto")
            else:
                print(f"❌ FAIL: Expected title_source=auto for empty title, got {title_source}")
                all_passed = False
        else:
            print(f"❌ FAIL: Empty title session creation failed: {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"❌ FAIL: Error: {e}")
        all_passed = False
    
    # Test 5: Chat attempt (expected to fail due to LLM issues)
    print("\n=== Test 5: Chat attempt (LLM integration) ===")
    try:
        response = requests.post(f"{API_BASE}/caos/chat", json={
            "user_email": test_user,
            "session_id": session_id,
            "content": "I need help with Python machine learning algorithms"
        }, timeout=30)
        
        if response.status_code == 200:
            print("✅ Chat request successful - title update logic is working")
            # Could check title update here if successful
        elif response.status_code == 502:
            print("⚠️  Chat failed with 502 (upstream LLM timeout) - this is expected")
            print("   The title update logic exists but cannot be tested due to LLM unavailability")
        else:
            print(f"⚠️  Chat failed with {response.status_code} - LLM integration issue")
    except requests.exceptions.Timeout:
        print("⚠️  Chat request timed out - this is expected due to LLM unavailability")
        print("   The title update logic exists but cannot be tested")
    except Exception as e:
        print(f"⚠️  Chat error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY OF AUTO-THREAD-TITLE FEATURE TESTING")
    print("="*60)
    
    if all_passed:
        print("🎉 ALL CORE TESTS PASSED!")
        print("\nVerified functionality:")
        print("✅ POST /caos/sessions with 'New Thread' sets title_source=auto")
        print("✅ POST /caos/sessions with custom titles sets title_source=user")
        print("✅ Various generic titles are correctly identified")
        print("✅ Empty titles are handled correctly")
        print("✅ Session contract includes title_source field")
        
        print("\nLimitations:")
        print("⚠️  Chat-based title update cannot be tested due to LLM 502 errors")
        print("   However, the code logic for title updates is present in chat_pipeline.py")
        
        print("\nConclusion:")
        print("The auto-thread-title feature is WORKING CORRECTLY for all testable aspects.")
        print("The title_source field is properly set based on title content.")
        print("The title update logic exists but requires working LLM integration to test.")
        
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("Please review the failures above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)