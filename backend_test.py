#!/usr/bin/env python3
"""
CAOS Preview Auth/Profile Flow Regression Test
Quick backend sanity check for auth and profile endpoints.
"""

import requests
import json
import sys

# Configuration
BASE_URL = "https://cognitive-shell.preview.emergentagent.com"
AUTH_HEADER = "Bearer test_session_b82ef2e35c02445c821a01d02179530a"
TEST_EMAIL = "seeded@example.com"

def test_auth_me():
    """Test GET /api/auth/me returns authenticated user"""
    print("🔍 Testing GET /api/auth/me...")
    
    url = f"{BASE_URL}/api/auth/me"
    headers = {"Authorization": AUTH_HEADER}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success - User: {data.get('email', 'N/A')}")
            print(f"   User ID: {data.get('user_id', 'N/A')}")
            print(f"   Name: {data.get('name', 'N/A')}")
            return True, data
        else:
            print(f"   ❌ Failed - {response.text}")
            return False, None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, None

def test_caos_profile():
    """Test GET /api/caos/profile/{email} succeeds for authenticated session"""
    print(f"🔍 Testing GET /api/caos/profile/{TEST_EMAIL}...")
    
    url = f"{BASE_URL}/api/caos/profile/{TEST_EMAIL}"
    headers = {"Authorization": AUTH_HEADER}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success - Profile loaded for: {data.get('user_email', 'N/A')}")
            
            # Check for assistant_name field
            assistant_name = data.get('assistant_name')
            if assistant_name:
                print(f"   📝 assistant_name found: '{assistant_name}'")
            else:
                print(f"   📝 assistant_name: Not present (None/empty)")
            
            # Show other key profile fields
            print(f"   Profile fields: {list(data.keys())}")
            return True, data
        else:
            print(f"   ❌ Failed - {response.text}")
            return False, None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, None

def main():
    """Run the regression sanity check"""
    print("=" * 60)
    print("CAOS Preview Auth/Profile Flow Regression Test")
    print("=" * 60)
    
    # Test 1: Auth endpoint
    auth_success, auth_data = test_auth_me()
    
    # Test 2: Profile endpoint  
    profile_success, profile_data = test_caos_profile()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if auth_success:
        print("✅ GET /api/auth/me - Working")
    else:
        print("❌ GET /api/auth/me - Failed")
    
    if profile_success:
        print("✅ GET /api/caos/profile/{email} - Working")
        if profile_data and profile_data.get('assistant_name'):
            print(f"✅ assistant_name field present: '{profile_data.get('assistant_name')}'")
        else:
            print("📝 assistant_name field: Not present (frontend will show first-run modal)")
    else:
        print("❌ GET /api/caos/profile/{email} - Failed")
    
    # Overall result
    if auth_success and profile_success:
        print("\n🎉 All tests passed - Auth/profile flow working correctly")
        return 0
    else:
        print("\n⚠️  Some tests failed - Check backend logs for details")
        return 1

if __name__ == "__main__":
    sys.exit(main())