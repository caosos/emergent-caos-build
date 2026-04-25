#!/usr/bin/env python3
"""
CAOS Link Persistence Endpoints Testing
Tests the link persistence functionality for sessions.
"""

import requests
import json
import time
from typing import Dict, Any, List

# Configuration from review request
BASE_URL = "https://caos-workspace-1.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"
AUTH_HEADER = "Bearer test_session_b82ef2e35c02445c821a01d02179530a"
TEST_USER_EMAIL = "seeded@example.com"
TEST_SESSION_ID = "3bba52d9-07f0-44d8-b7e8-fc4afd7966d4"

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
            print(f"❌ {test_name}: {details}")
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

def make_request(method: str, url: str, **kwargs) -> requests.Response:
    """Make HTTP request with auth header and error handling."""
    try:
        headers = kwargs.get('headers', {})
        headers['Authorization'] = AUTH_HEADER
        kwargs['headers'] = headers
        
        response = requests.request(method, url, timeout=30, **kwargs)
        return response
    except requests.exceptions.Timeout:
        print(f"⚠️  Request timeout for {method} {url}")
        return None
    except Exception as e:
        print(f"⚠️  Request error for {method} {url}: {e}")
        return None

def test_link_persistence():
    """Test the complete link persistence functionality."""
    results = TestResults()
    
    print(f"🚀 Testing CAOS Link Persistence Endpoints")
    print(f"Base URL: {BASE_URL}")
    print(f"User: {TEST_USER_EMAIL}")
    print(f"Session ID: {TEST_SESSION_ID}")
    
    # Test 1: POST /api/caos/sessions/{session_id}/links - Create manual link
    print("\n=== Test 1: POST link creation (manual) ===")
    
    manual_link_payload = {
        "url": "https://backend-check.example/test",
        "label": "Backend Check",
        "source": "manual"
    }
    
    post_url = f"{API_BASE}/caos/sessions/{TEST_SESSION_ID}/links"
    response = make_request("POST", post_url, json=manual_link_payload)
    
    if response is None:
        results.add_result("POST manual link creation", False, "Request timed out")
    elif response.status_code == 200:
        try:
            link_data = response.json()
            # Check if response contains expected fields
            required_fields = ["id", "user_email", "session_id", "url", "normalized_url", "label", "host", "source", "mention_count", "created_at", "updated_at"]
            missing_fields = [field for field in required_fields if field not in link_data]
            
            if not missing_fields:
                results.add_result(
                    "POST manual link creation", 
                    True, 
                    f"Manual link created successfully with all required fields. ID: {link_data.get('id')}"
                )
                # Store the created link ID for later tests
                manual_link_id = link_data.get('id')
            else:
                results.add_result(
                    "POST manual link creation", 
                    False, 
                    f"Response missing required fields: {missing_fields}"
                )
                manual_link_id = None
        except json.JSONDecodeError:
            results.add_result("POST manual link creation", False, f"Invalid JSON response: {response.text}")
            manual_link_id = None
    else:
        results.add_result(
            "POST manual link creation", 
            False, 
            f"HTTP {response.status_code}: {response.text}"
        )
        manual_link_id = None
    
    # Test 2: POST another link with different source (auto)
    print("\n=== Test 2: POST link creation (auto) ===")
    
    auto_link_payload = {
        "url": "https://docs.python.org/3/library/asyncio.html",
        "label": "Python Asyncio Documentation",
        "source": "auto"
    }
    
    response = make_request("POST", post_url, json=auto_link_payload)
    
    if response is None:
        results.add_result("POST auto link creation", False, "Request timed out")
    elif response.status_code == 200:
        try:
            link_data = response.json()
            if link_data.get('source') == 'auto':
                results.add_result(
                    "POST auto link creation", 
                    True, 
                    f"Auto link created successfully. ID: {link_data.get('id')}"
                )
                auto_link_id = link_data.get('id')
            else:
                results.add_result(
                    "POST auto link creation", 
                    False, 
                    f"Source field incorrect. Expected 'auto', got '{link_data.get('source')}'"
                )
                auto_link_id = None
        except json.JSONDecodeError:
            results.add_result("POST auto link creation", False, f"Invalid JSON response: {response.text}")
            auto_link_id = None
    else:
        results.add_result(
            "POST auto link creation", 
            False, 
            f"HTTP {response.status_code}: {response.text}"
        )
        auto_link_id = None
    
    # Test 3: GET /api/caos/sessions/{session_id}/links - Retrieve links
    print("\n=== Test 3: GET links retrieval ===")
    
    get_url = f"{API_BASE}/caos/sessions/{TEST_SESSION_ID}/links"
    response = make_request("GET", get_url)
    
    if response is None:
        results.add_result("GET links retrieval", False, "Request timed out")
    elif response.status_code == 200:
        try:
            links_data = response.json()
            
            if isinstance(links_data, list):
                # Check if our created links are present
                manual_found = any(link.get('source') == 'manual' and link.get('url') == 'https://backend-check.example/test' for link in links_data)
                auto_found = any(link.get('source') == 'auto' and link.get('url') == 'https://docs.python.org/3/library/asyncio.html' for link in links_data)
                
                if manual_found and auto_found:
                    results.add_result(
                        "GET links retrieval", 
                        True, 
                        f"Retrieved {len(links_data)} links including both manual and auto links"
                    )
                elif manual_found:
                    results.add_result(
                        "GET links retrieval", 
                        True, 
                        f"Retrieved {len(links_data)} links including manual link (auto link may not have been created)"
                    )
                else:
                    results.add_result(
                        "GET links retrieval", 
                        False, 
                        f"Retrieved {len(links_data)} links but created links not found"
                    )
                
                # Verify field structure of returned links
                if len(links_data) > 0:
                    sample_link = links_data[0]
                    required_fields = ["id", "user_email", "session_id", "url", "normalized_url", "label", "host", "source", "mention_count", "created_at", "updated_at"]
                    missing_fields = [field for field in required_fields if field not in sample_link]
                    
                    if not missing_fields:
                        results.add_result(
                            "GET links field structure", 
                            True, 
                            f"All required fields present in link records"
                        )
                    else:
                        results.add_result(
                            "GET links field structure", 
                            False, 
                            f"Missing fields in link records: {missing_fields}"
                        )
                    
                    # Verify session scoping
                    session_scoped = all(link.get('session_id') == TEST_SESSION_ID for link in links_data)
                    if session_scoped:
                        results.add_result(
                            "Session scoping", 
                            True, 
                            f"All links correctly scoped to session {TEST_SESSION_ID}"
                        )
                    else:
                        wrong_sessions = [link.get('session_id') for link in links_data if link.get('session_id') != TEST_SESSION_ID]
                        results.add_result(
                            "Session scoping", 
                            False, 
                            f"Found links with wrong session IDs: {wrong_sessions}"
                        )
                else:
                    results.add_result(
                        "GET links field structure", 
                        False, 
                        "No links returned to verify field structure"
                    )
            else:
                results.add_result(
                    "GET links retrieval", 
                    False, 
                    f"Expected list response, got: {type(links_data)}"
                )
        except json.JSONDecodeError:
            results.add_result("GET links retrieval", False, f"Invalid JSON response: {response.text}")
    else:
        results.add_result(
            "GET links retrieval", 
            False, 
            f"HTTP {response.status_code}: {response.text}"
        )
    
    # Test 4: Test authentication - try without auth header
    print("\n=== Test 4: Authentication verification ===")
    
    # Make request without auth header
    response = requests.get(get_url, timeout=30)
    
    if response.status_code == 401:
        results.add_result(
            "Authentication required", 
            True, 
            f"Correctly returns 401 without auth header"
        )
    else:
        results.add_result(
            "Authentication required", 
            False, 
            f"Expected 401 without auth, got {response.status_code}"
        )
    
    # Test 5: Test with invalid session ID
    print("\n=== Test 5: Invalid session ID handling ===")
    
    invalid_session_url = f"{API_BASE}/caos/sessions/invalid-session-id/links"
    response = make_request("GET", invalid_session_url)
    
    if response is None:
        results.add_result("Invalid session ID handling", False, "Request timed out")
    elif response.status_code in [404, 422]:
        results.add_result(
            "Invalid session ID handling", 
            True, 
            f"Correctly handles invalid session ID with {response.status_code}"
        )
    else:
        results.add_result(
            "Invalid session ID handling", 
            False, 
            f"Unexpected response for invalid session ID: {response.status_code}"
        )
    
    # Test 6: Test POST with invalid data
    print("\n=== Test 6: Invalid POST data handling ===")
    
    invalid_payload = {
        "url": "not-a-valid-url",
        "label": "",  # Empty label
        "source": "invalid_source"  # Invalid source
    }
    
    response = make_request("POST", post_url, json=invalid_payload)
    
    if response is None:
        results.add_result("Invalid POST data handling", False, "Request timed out")
    elif response.status_code in [400, 422]:
        results.add_result(
            "Invalid POST data handling", 
            True, 
            f"Correctly rejects invalid data with {response.status_code}"
        )
    else:
        results.add_result(
            "Invalid POST data handling", 
            False, 
            f"Unexpected response for invalid data: {response.status_code} - {response.text}"
        )
    
    return results

def main():
    """Run all link persistence tests."""
    try:
        results = test_link_persistence()
        success = results.summary()
        
        if success:
            print("\n🎉 All link persistence tests passed!")
        else:
            print(f"\n❌ Some link persistence tests failed. Please review the failures above.")
            
        return success
        
    except Exception as e:
        print(f"\n💥 Test execution failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)