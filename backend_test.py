#!/usr/bin/env python3
"""
CAOS Backend Testing Suite
Tests the CAOS backend routing and memory update after portable-runtime implementation.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict

import aiohttp


class CaosBackendTester:
    def __init__(self, base_url: str = "https://deno-env-review.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.test_user_email = f"test-user-{uuid.uuid4().hex[:8]}@example.com"
        self.session_id = None
        self.results = []
        
    async def log_result(self, test_name: str, success: bool, details: str, response_data: Any = None):
        """Log test result with details"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        if response_data and not success:
            print(f"   Response: {json.dumps(response_data, indent=2)}")

    async def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> tuple[int, Any]:
        """Make HTTP request and return status code and response data"""
        url = f"{self.base_url}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            try:
                if method.upper() == "GET":
                    async with session.get(url, params=params) as response:
                        status = response.status
                        try:
                            response_data = await response.json()
                        except:
                            response_data = await response.text()
                        return status, response_data
                elif method.upper() == "POST":
                    headers = {"Content-Type": "application/json"}
                    async with session.post(url, json=data, headers=headers, params=params) as response:
                        status = response.status
                        try:
                            response_data = await response.json()
                        except:
                            response_data = await response.text()
                        return status, response_data
                else:
                    return 400, {"error": f"Unsupported method: {method}"}
            except Exception as e:
                return 500, {"error": str(e)}

    async def test_1_get_runtime_settings_default(self):
        """Test 1: GET /caos/runtime/settings/{user_email} returns default hybrid runtime settings"""
        status, data = await self.make_request("GET", f"/caos/runtime/settings/{self.test_user_email}")
        
        if status != 200:
            await self.log_result("GET Runtime Settings Default", False, f"Expected 200, got {status}", data)
            return False
            
        # Verify response structure and default values
        required_fields = ["user_email", "key_source", "default_provider", "default_model", "enabled_providers", "provider_catalog"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            await self.log_result("GET Runtime Settings Default", False, f"Missing fields: {missing_fields}", data)
            return False
            
        # Verify default values
        if data["key_source"] != "hybrid":
            await self.log_result("GET Runtime Settings Default", False, f"Expected key_source 'hybrid', got '{data['key_source']}'", data)
            return False
            
        # Verify provider catalog includes required providers
        catalog = data.get("provider_catalog", [])
        provider_names = [p["provider"] for p in catalog]
        required_providers = ["openai", "anthropic", "gemini", "xai"]
        missing_providers = [p for p in required_providers if p not in provider_names]
        
        if missing_providers:
            await self.log_result("GET Runtime Settings Default", False, f"Missing providers in catalog: {missing_providers}", data)
            return False
            
        # Verify xAI requires custom key
        xai_provider = next((p for p in catalog if p["provider"] == "xai"), None)
        if not xai_provider or not xai_provider.get("requires_custom_key"):
            await self.log_result("GET Runtime Settings Default", False, "xAI provider should require custom key", data)
            return False
            
        await self.log_result("GET Runtime Settings Default", True, "Default hybrid runtime settings returned correctly", data)
        return True

    async def test_2_post_runtime_settings_persist(self):
        """Test 2: POST /caos/runtime/settings can persist a preferred provider/model"""
        settings_data = {
            "user_email": self.test_user_email,
            "key_source": "hybrid",
            "default_provider": "anthropic",
            "default_model": "claude-sonnet-4-5-20250929",
            "enabled_providers": ["openai", "anthropic", "gemini", "xai"]
        }
        
        status, data = await self.make_request("POST", "/caos/runtime/settings", settings_data)
        
        if status != 200:
            await self.log_result("POST Runtime Settings Persist", False, f"Expected 200, got {status}", data)
            return False
            
        # Verify the settings were persisted correctly
        if data.get("default_provider") != "anthropic":
            await self.log_result("POST Runtime Settings Persist", False, f"Expected default_provider 'anthropic', got '{data.get('default_provider')}'", data)
            return False
            
        if data.get("default_model") != "claude-sonnet-4-5-20250929":
            await self.log_result("POST Runtime Settings Persist", False, f"Expected default_model 'claude-sonnet-4-5-20250929', got '{data.get('default_model')}'", data)
            return False
            
        await self.log_result("POST Runtime Settings Persist", True, "Runtime settings persisted successfully", data)
        return True

    async def test_3_post_sessions_create(self):
        """Test 3: POST /caos/sessions creates a session for the test user"""
        session_data = {
            "user_email": self.test_user_email,
            "title": f"Test Session {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        status, data = await self.make_request("POST", "/caos/sessions", session_data)
        
        if status != 200:
            await self.log_result("POST Sessions Create", False, f"Expected 200, got {status}", data)
            return False
            
        # Verify session was created with correct structure
        required_fields = ["session_id", "user_email", "title", "created_at", "updated_at"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            await self.log_result("POST Sessions Create", False, f"Missing fields: {missing_fields}", data)
            return False
            
        if data["user_email"] != self.test_user_email:
            await self.log_result("POST Sessions Create", False, f"Expected user_email '{self.test_user_email}', got '{data['user_email']}'", data)
            return False
            
        # Store session_id for subsequent tests
        self.session_id = data["session_id"]
        await self.log_result("POST Sessions Create", True, f"Session created successfully with ID: {self.session_id}", data)
        return True

    async def test_4_post_chat_with_runtime_resolution(self):
        """Test 4: POST /caos/chat works with runtime resolution from stored settings"""
        if not self.session_id:
            await self.log_result("POST Chat Runtime Resolution", False, "No session_id available from previous test", None)
            return False
            
        chat_data = {
            "user_email": self.test_user_email,
            "session_id": self.session_id,
            "content": "Hello, can you help me understand how CAOS memory works?",
            # Intentionally omitting provider and model to test runtime resolution
        }
        
        status, data = await self.make_request("POST", "/caos/chat", chat_data)
        
        if status != 200:
            await self.log_result("POST Chat Runtime Resolution", False, f"Expected 200, got {status}", data)
            return False
            
        # Verify response structure includes required fields
        required_fields = ["session_id", "reply", "provider", "model", "subject_bins", "receipt"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            await self.log_result("POST Chat Runtime Resolution", False, f"Missing fields: {missing_fields}", data)
            return False
            
        # Verify runtime resolution used anthropic (from test 2)
        if data.get("provider") != "anthropic":
            await self.log_result("POST Chat Runtime Resolution", False, f"Expected provider 'anthropic' from stored settings, got '{data.get('provider')}'", data)
            return False
            
        if data.get("model") != "claude-sonnet-4-5-20250929":
            await self.log_result("POST Chat Runtime Resolution", False, f"Expected model 'claude-sonnet-4-5-20250929' from stored settings, got '{data.get('model')}'", data)
            return False
            
        await self.log_result("POST Chat Runtime Resolution", True, "Chat worked with runtime resolution from stored settings", data)
        return True

    async def test_5_chat_response_fields(self):
        """Test 5: Chat response includes provider, model, subject_bins, and receipt fields"""
        if not self.session_id:
            await self.log_result("Chat Response Fields", False, "No session_id available from previous test", None)
            return False
            
        chat_data = {
            "user_email": self.test_user_email,
            "session_id": self.session_id,
            "content": "What are the key features of this AI workspace?",
        }
        
        status, data = await self.make_request("POST", "/caos/chat", chat_data)
        
        if status != 200:
            await self.log_result("Chat Response Fields", False, f"Expected 200, got {status}", data)
            return False
            
        # Verify all required fields are present
        required_fields = ["provider", "model", "subject_bins", "receipt"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            await self.log_result("Chat Response Fields", False, f"Missing required fields: {missing_fields}", data)
            return False
            
        # Verify receipt contains expected sub-fields
        receipt = data.get("receipt", {})
        receipt_required_fields = ["selected_summary_ids", "selected_seed_ids"]
        receipt_missing_fields = [field for field in receipt_required_fields if field not in receipt]
        
        if receipt_missing_fields:
            await self.log_result("Chat Response Fields", False, f"Missing receipt fields: {receipt_missing_fields}", data)
            return False
            
        # Verify subject_bins is a list
        if not isinstance(data.get("subject_bins"), list):
            await self.log_result("Chat Response Fields", False, f"subject_bins should be a list, got {type(data.get('subject_bins'))}", data)
            return False
            
        await self.log_result("Chat Response Fields", True, "Chat response includes all required fields", data)
        return True

    async def test_6_xai_grok_byo_settings_and_failure(self):
        """Test 6: xAI + grok settings save succeeds, but chat fails with BYO key message"""
        # First, update settings to use xAI
        settings_data = {
            "user_email": self.test_user_email,
            "key_source": "hybrid",
            "default_provider": "xai",
            "default_model": "grok-byo-placeholder",
            "enabled_providers": ["openai", "anthropic", "gemini", "xai"]
        }
        
        status, data = await self.make_request("POST", "/caos/runtime/settings", settings_data)
        
        if status != 200:
            await self.log_result("xAI Grok BYO Settings Save", False, f"Settings save failed with status {status}", data)
            return False
            
        await self.log_result("xAI Grok BYO Settings Save", True, "xAI + grok settings saved successfully", data)
        
        # Now try to chat with xAI - this should fail cleanly
        if not self.session_id:
            await self.log_result("xAI Grok BYO Chat Failure", False, "No session_id available", None)
            return False
            
        chat_data = {
            "user_email": self.test_user_email,
            "session_id": self.session_id,
            "content": "Test message for xAI provider",
        }
        
        status, data = await self.make_request("POST", "/caos/chat", chat_data)
        
        # Should fail with 404 (ValueError converted to 404 in the route)
        if status == 500:
            await self.log_result("xAI Grok BYO Chat Failure", False, "Chat failed with 500 error instead of clean failure", data)
            return False
            
        if status != 404:
            await self.log_result("xAI Grok BYO Chat Failure", False, f"Expected 404 for BYO key required, got {status}", data)
            return False
            
        # Verify error message mentions BYO key requirement
        error_detail = data.get("detail", "").lower() if isinstance(data, dict) else str(data).lower()
        byo_keywords = ["bring", "key", "credentials", "xai", "grok"]
        
        if not any(keyword in error_detail for keyword in byo_keywords):
            await self.log_result("xAI Grok BYO Chat Failure", False, f"Error message doesn't mention BYO key requirement: {error_detail}", data)
            return False
            
        await self.log_result("xAI Grok BYO Chat Failure", True, "Chat failed cleanly with BYO key required message", data)
        return True

    async def test_7_no_500_errors_in_flow(self):
        """Test 7: Ensure no 500 errors occur in the above flow"""
        # This test is implicit - if any of the above tests encountered a 500 error,
        # it would have been logged. We'll check our results for any 500 errors.
        
        error_500_tests = [result for result in self.results if "500" in result.get("details", "")]
        
        if error_500_tests:
            test_names = [test["test"] for test in error_500_tests]
            await self.log_result("No 500 Errors", False, f"Found 500 errors in tests: {test_names}", error_500_tests)
            return False
            
        await self.log_result("No 500 Errors", True, "No 500 errors encountered in the test flow", None)
        return True

    async def run_all_tests(self):
        """Run all tests in sequence"""
        print(f"🚀 Starting CAOS Backend Testing Suite")
        print(f"📧 Test user: {self.test_user_email}")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        tests = [
            self.test_1_get_runtime_settings_default,
            self.test_2_post_runtime_settings_persist,
            self.test_3_post_sessions_create,
            self.test_4_post_chat_with_runtime_resolution,
            self.test_5_chat_response_fields,
            self.test_6_xai_grok_byo_settings_and_failure,
            self.test_7_no_500_errors_in_flow,
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                success = await test()
                if success:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                await self.log_result(test.__name__, False, f"Test threw exception: {str(e)}", None)
                failed += 1
            
            print()  # Add spacing between tests
        
        print("=" * 80)
        print(f"📊 Test Results: {passed} passed, {failed} failed")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['details']}")
        
        return failed == 0


async def main():
    """Main test runner"""
    tester = CaosBackendTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! CAOS backend is working correctly.")
        return 0
    else:
        print("\n💥 Some tests failed. Check the details above.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))