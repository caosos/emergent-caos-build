#!/usr/bin/env python3
"""
Quick verification of existing links in the test session
"""

import requests
import json

BASE_URL = "https://caos-workspace-1.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"
AUTH_HEADER = "Bearer test_session_b82ef2e35c02445c821a01d02179530a"
TEST_SESSION_ID = "3bba52d9-07f0-44d8-b7e8-fc4afd7966d4"

def check_existing_links():
    """Check what links currently exist in the test session."""
    
    headers = {'Authorization': AUTH_HEADER}
    get_url = f"{API_BASE}/caos/sessions/{TEST_SESSION_ID}/links"
    
    try:
        response = requests.get(get_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            links = response.json()
            print(f"Found {len(links)} links in session {TEST_SESSION_ID}:")
            print()
            
            for i, link in enumerate(links, 1):
                print(f"{i}. {link.get('label', 'No label')}")
                print(f"   URL: {link.get('url')}")
                print(f"   Source: {link.get('source')}")
                print(f"   Host: {link.get('host')}")
                print(f"   Mention Count: {link.get('mention_count', 0)}")
                print(f"   Created: {link.get('created_at')}")
                print()
            
            # Check for both auto and manual sources
            auto_links = [l for l in links if l.get('source') == 'auto']
            manual_links = [l for l in links if l.get('source') == 'manual']
            
            print(f"Summary:")
            print(f"- Auto links: {len(auto_links)}")
            print(f"- Manual links: {len(manual_links)}")
            print(f"- Total links: {len(links)}")
            
            return True
        else:
            print(f"Failed to retrieve links: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error checking links: {e}")
        return False

if __name__ == "__main__":
    check_existing_links()