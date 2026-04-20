#!/usr/bin/env python3
"""
CAOS Pre-Deploy Backend Sanity Pass
Tests core readiness for deployment on https://memory-hub-63.preview.emergentagent.com/api

Focus areas:
1. Session creation endpoint works
2. Chat/message endpoint works for a normal turn
3. Sessions listing works after chat
4. Artifacts endpoint works for the session
5. Continuity endpoint works for the session
6. Runtime settings endpoint works
7. Voice settings endpoint works
8. No 500s or contract-breaking responses in the sanity flow
"""

import asyncio
import json
import sys
import time
from typing import Any, Dict

import aiohttp


# Configuration
BACKEND_URL = "https://memory-hub-63.preview.emergentagent.com/api"
TEST_USER_EMAIL = "sanity-test-user@example.com"


class SanityTestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.blockers = []
        
    def assert_true(self, condition: bool, message: str, is_blocker: bool = False):
        if condition:
            self.passed += 1
            print(f"✅ {message}")
        else:
            self.failed += 1
            self.errors.append(message)
            if is_blocker:
                self.blockers.append(message)
            print(f"❌ {message}")
            
    def assert_status_not_500(self, status: int, endpoint: str, is_blocker: bool = True):
        if status != 500:
            self.passed += 1
            print(f"✅ {endpoint} - No 500 error (status: {status})")
        else:
            self.failed += 1
            error_msg = f"{endpoint} - Returned 500 error"
            self.errors.append(error_msg)
            if is_blocker:
                self.blockers.append(error_msg)
            print(f"❌ {error_msg}")
            
    def assert_not_none(self, value: Any, message: str, is_blocker: bool = False):
        if value is not None:
            self.passed += 1
            print(f"✅ {message}")
        else:
            self.failed += 1
            self.errors.append(message)
            if is_blocker:
                self.blockers.append(message)
            print(f"❌ {message}")
            
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 Sanity Test Summary: {self.passed}/{total} passed")
        
        if self.blockers:
            print(f"\n🚨 DEPLOYMENT BLOCKERS ({len(self.blockers)}):")
            for blocker in self.blockers:
                print(f"  - {blocker}")
                
        if self.errors and not self.blockers:
            print(f"\n⚠️  Non-blocking issues ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
                
        if not self.blockers:
            print("\n🎉 DEPLOYMENT READY - No blockers found")
        else:
            print(f"\n🛑 NOT READY FOR DEPLOYMENT - {len(self.blockers)} blockers found")
            
        return len(self.blockers) == 0


async def make_request(session: aiohttp.ClientSession, method: str, endpoint: str, data: Dict = None, json_data: Dict = None) -> tuple[Dict, int]:
    """Make HTTP request and return JSON response and status code"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        async with session.request(method, url, json=json_data, data=data) as response:
            status = response.status
            if response.status >= 400:
                text = await response.text()
                print(f"⚠️  HTTP {response.status} for {method} {endpoint}: {text}")
                return {"error": f"HTTP {response.status}", "detail": text}, status
            return await response.json(), status
    except Exception as e:
        print(f"❌ Request failed for {method} {endpoint}: {e}")
        return {"error": "request_failed", "detail": str(e)}, 0


async def test_session_creation(session: aiohttp.ClientSession, result: SanityTestResult) -> str:
    """Test 1: Session creation endpoint works"""
    print("\n🧪 Test 1: Session creation endpoint")
    
    session_data = {
        "user_email": TEST_USER_EMAIL,
        "title": "Sanity Test Session"
    }
    response, status = await make_request(session, "POST", "/caos/sessions", json_data=session_data)
    
    result.assert_status_not_500(status, "POST /caos/sessions", is_blocker=True)
    result.assert_true("error" not in response, "Session creation should succeed", is_blocker=True)
    result.assert_not_none(response.get("session_id"), "Session should return session_id", is_blocker=True)
    result.assert_not_none(response.get("user_email"), "Session should return user_email", is_blocker=True)
    
    return response.get("session_id")


async def test_chat_endpoint(session: aiohttp.ClientSession, result: SanityTestResult, session_id: str):
    """Test 2: Chat/message endpoint works for a normal turn"""
    print("\n🧪 Test 2: Chat/message endpoint")
    
    if not session_id:
        result.assert_true(False, "Cannot test chat - no session_id from previous test", is_blocker=True)
        return
    
    chat_data = {
        "user_email": TEST_USER_EMAIL,
        "session_id": session_id,
        "content": "Hello, this is a sanity test message. Please respond briefly."
    }
    response, status = await make_request(session, "POST", "/caos/chat", json_data=chat_data)
    
    result.assert_status_not_500(status, "POST /caos/chat", is_blocker=True)
    result.assert_true("error" not in response, "Chat request should succeed", is_blocker=True)
    result.assert_not_none(response.get("reply"), "Chat should return reply", is_blocker=True)
    result.assert_not_none(response.get("provider"), "Chat should return provider", is_blocker=False)
    result.assert_not_none(response.get("model"), "Chat should return model", is_blocker=False)


async def test_sessions_listing(session: aiohttp.ClientSession, result: SanityTestResult):
    """Test 3: Sessions listing works after chat"""
    print("\n🧪 Test 3: Sessions listing")
    
    response, status = await make_request(session, "GET", f"/caos/sessions?user_email={TEST_USER_EMAIL}")
    
    result.assert_status_not_500(status, "GET /caos/sessions", is_blocker=True)
    result.assert_true("error" not in response, "Sessions listing should succeed", is_blocker=True)
    result.assert_true(isinstance(response, list), "Sessions should return a list", is_blocker=True)
    result.assert_true(len(response) > 0, "Should have at least one session after creation", is_blocker=False)


async def test_artifacts_endpoint(session: aiohttp.ClientSession, result: SanityTestResult, session_id: str):
    """Test 4: Artifacts endpoint works for the session"""
    print("\n🧪 Test 4: Artifacts endpoint")
    
    if not session_id:
        result.assert_true(False, "Cannot test artifacts - no session_id from previous test", is_blocker=True)
        return
    
    response, status = await make_request(session, "GET", f"/caos/sessions/{session_id}/artifacts")
    
    result.assert_status_not_500(status, f"GET /caos/sessions/{session_id}/artifacts", is_blocker=True)
    result.assert_true("error" not in response, "Artifacts endpoint should succeed", is_blocker=True)
    result.assert_not_none(response.get("receipts"), "Artifacts should include receipts", is_blocker=False)
    result.assert_not_none(response.get("summaries"), "Artifacts should include summaries", is_blocker=False)
    result.assert_not_none(response.get("seeds"), "Artifacts should include seeds", is_blocker=False)


async def test_continuity_endpoint(session: aiohttp.ClientSession, result: SanityTestResult, session_id: str):
    """Test 5: Continuity endpoint works for the session"""
    print("\n🧪 Test 5: Continuity endpoint")
    
    if not session_id:
        result.assert_true(False, "Cannot test continuity - no session_id from previous test", is_blocker=True)
        return
    
    response, status = await make_request(session, "GET", f"/caos/sessions/{session_id}/continuity")
    
    result.assert_status_not_500(status, f"GET /caos/sessions/{session_id}/continuity", is_blocker=True)
    result.assert_true("error" not in response, "Continuity endpoint should succeed", is_blocker=True)
    result.assert_not_none(response.get("session_id"), "Continuity should include session_id", is_blocker=False)
    result.assert_not_none(response.get("lineage_depth"), "Continuity should include lineage_depth", is_blocker=False)


async def test_runtime_settings(session: aiohttp.ClientSession, result: SanityTestResult):
    """Test 6: Runtime settings endpoint works"""
    print("\n🧪 Test 6: Runtime settings endpoint")
    
    # Test GET runtime settings
    response, status = await make_request(session, "GET", f"/caos/runtime/settings/{TEST_USER_EMAIL}")
    
    result.assert_status_not_500(status, f"GET /caos/runtime/settings/{TEST_USER_EMAIL}", is_blocker=True)
    result.assert_true("error" not in response, "Runtime settings GET should succeed", is_blocker=True)
    result.assert_not_none(response.get("user_email"), "Runtime settings should include user_email", is_blocker=False)
    result.assert_not_none(response.get("provider_catalog"), "Runtime settings should include provider_catalog", is_blocker=False)
    
    # Test POST runtime settings (basic update)
    settings_data = {
        "user_email": TEST_USER_EMAIL,
        "key_source": "hybrid",
        "default_provider": "openai",
        "default_model": "gpt-5.2",
        "enabled_providers": ["openai", "anthropic"]
    }
    response, status = await make_request(session, "POST", "/caos/runtime/settings", json_data=settings_data)
    
    result.assert_status_not_500(status, "POST /caos/runtime/settings", is_blocker=True)
    result.assert_true("error" not in response, "Runtime settings POST should succeed", is_blocker=True)


async def test_voice_settings(session: aiohttp.ClientSession, result: SanityTestResult):
    """Test 7: Voice settings endpoint works"""
    print("\n🧪 Test 7: Voice settings endpoint")
    
    # Test GET voice settings
    response, status = await make_request(session, "GET", f"/caos/voice/settings/{TEST_USER_EMAIL}")
    
    result.assert_status_not_500(status, f"GET /caos/voice/settings/{TEST_USER_EMAIL}", is_blocker=True)
    result.assert_true("error" not in response, "Voice settings GET should succeed", is_blocker=True)
    result.assert_not_none(response.get("user_email"), "Voice settings should include user_email", is_blocker=False)
    result.assert_not_none(response.get("voice_preferences"), "Voice settings should include voice_preferences", is_blocker=False)
    
    # Test POST voice settings (basic update)
    voice_data = {
        "user_email": TEST_USER_EMAIL,
        "stt_primary_model": "gpt-4o-transcribe",
        "stt_fallback_model": "whisper-1",
        "stt_language": "en",
        "tts_voice": "nova",
        "tts_model": "tts-1-hd",
        "tts_speed": 1.0
    }
    response, status = await make_request(session, "POST", "/caos/voice/settings", json_data=voice_data)
    
    result.assert_status_not_500(status, "POST /caos/voice/settings", is_blocker=True)
    result.assert_true("error" not in response, "Voice settings POST should succeed", is_blocker=True)


async def test_no_500_errors_summary(session: aiohttp.ClientSession, result: SanityTestResult):
    """Test 8: Summary check for 500 errors in the sanity flow"""
    print("\n🧪 Test 8: No 500 errors summary")
    
    # This is implicitly tested by all the assert_status_not_500 calls above
    # Just provide a summary message
    blocker_500s = [error for error in result.blockers if "500 error" in error]
    if not blocker_500s:
        result.assert_true(True, "No 500 errors detected in sanity flow", is_blocker=False)
    else:
        result.assert_true(False, f"Found {len(blocker_500s)} 500 errors in sanity flow", is_blocker=True)


async def run_sanity_tests():
    """Run all pre-deploy sanity tests"""
    print("🚀 Starting CAOS Pre-Deploy Backend Sanity Pass")
    print(f"🎯 Testing against: {BACKEND_URL}")
    print("📋 Focus: Core readiness, not exhaustive QA")
    
    result = SanityTestResult()
    session_id = None
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test 1: Session creation
            session_id = await test_session_creation(session, result)
            
            # Test 2: Chat endpoint
            await test_chat_endpoint(session, result, session_id)
            
            # Small delay to allow backend processing
            await asyncio.sleep(1)
            
            # Test 3: Sessions listing
            await test_sessions_listing(session, result)
            
            # Test 4: Artifacts endpoint
            await test_artifacts_endpoint(session, result, session_id)
            
            # Test 5: Continuity endpoint
            await test_continuity_endpoint(session, result, session_id)
            
            # Test 6: Runtime settings
            await test_runtime_settings(session, result)
            
            # Test 7: Voice settings
            await test_voice_settings(session, result)
            
            # Test 8: 500 errors summary
            await test_no_500_errors_summary(session, result)
            
        except Exception as e:
            print(f"❌ Sanity test execution failed: {e}")
            result.errors.append(f"Test execution failed: {e}")
            result.blockers.append(f"Test execution failed: {e}")
            result.failed += 1
    
    return result.summary()


if __name__ == "__main__":
    print("=" * 80)
    print("CAOS PRE-DEPLOY BACKEND SANITY PASS")
    print("=" * 80)
    
    success = asyncio.run(run_sanity_tests())
    
    print("\n" + "=" * 80)
    if success:
        print("✅ SANITY PASS COMPLETE - READY FOR DEPLOYMENT")
    else:
        print("❌ SANITY PASS FAILED - DEPLOYMENT BLOCKED")
    print("=" * 80)
    
    sys.exit(0 if success else 1)