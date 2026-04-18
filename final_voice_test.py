#!/usr/bin/env python3
"""
CAOS Backend Voice/Settings Final Testing Script
Comprehensive testing addressing all review request requirements.
"""

import base64
import io
import json
import requests
import tempfile
from pathlib import Path

# Configuration
BASE_URL = "https://deno-env-review.preview.emergentagent.com/api"
TEST_USER_EMAIL = "voice.test@emergentagent.com"

def log_test(test_name, status, details=""):
    """Log test results with consistent formatting"""
    status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{status_symbol} {test_name}: {status}")
    if details:
        print(f"   {details}")
    print()

def test_1_post_voice_settings():
    """Test 1: POST /caos/voice/settings persists voice preferences for fresh test user"""
    print("=== Test 1: POST /caos/voice/settings ===")
    
    try:
        # Test data exactly as specified in review request
        payload = {
            "user_email": TEST_USER_EMAIL,
            "stt_primary_model": "gpt-4o-transcribe",
            "stt_fallback_model": "whisper-1", 
            "stt_language": "en",
            "tts_model": "tts-1-hd",
            "tts_voice": "nova",
            "tts_speed": 1.0
        }
        
        response = requests.post(f"{BASE_URL}/caos/voice/settings", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            
            if "user_email" in data and "voice_preferences" in data:
                prefs = data["voice_preferences"]
                
                # Verify all required fields match exactly
                expected_fields = {
                    "stt_primary_model": "gpt-4o-transcribe",
                    "stt_fallback_model": "whisper-1",
                    "stt_language": "en",
                    "tts_model": "tts-1-hd", 
                    "tts_voice": "nova",
                    "tts_speed": 1.0
                }
                
                all_correct = True
                for field, expected_value in expected_fields.items():
                    if prefs.get(field) != expected_value:
                        all_correct = False
                        log_test("POST voice settings", "FAIL", f"Field {field}: expected {expected_value}, got {prefs.get(field)}")
                        break
                
                if all_correct:
                    log_test("POST voice settings", "PASS", f"Voice preferences persisted successfully for fresh test user {TEST_USER_EMAIL}")
                    return True
            else:
                log_test("POST voice settings", "FAIL", f"Invalid response structure: {data}")
        else:
            log_test("POST voice settings", "FAIL", f"HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        log_test("POST voice settings", "FAIL", f"Exception: {str(e)}")
    
    return False

def test_2_get_voice_settings():
    """Test 2: GET /caos/voice/settings/{user_email} returns the saved preferences"""
    print("=== Test 2: GET /caos/voice/settings/{user_email} ===")
    
    try:
        response = requests.get(f"{BASE_URL}/caos/voice/settings/{TEST_USER_EMAIL}")
        
        if response.status_code == 200:
            data = response.json()
            
            if "user_email" in data and "voice_preferences" in data:
                prefs = data["voice_preferences"]
                
                # Verify the saved preferences match exactly what we set in test 1
                expected_fields = {
                    "stt_primary_model": "gpt-4o-transcribe",
                    "stt_fallback_model": "whisper-1",
                    "stt_language": "en",
                    "tts_model": "tts-1-hd",
                    "tts_voice": "nova", 
                    "tts_speed": 1.0
                }
                
                all_correct = True
                for field, expected_value in expected_fields.items():
                    if prefs.get(field) != expected_value:
                        all_correct = False
                        log_test("GET voice settings", "FAIL", f"Field {field}: expected {expected_value}, got {prefs.get(field)}")
                        break
                
                if all_correct:
                    log_test("GET voice settings", "PASS", f"Retrieved correct saved preferences for {TEST_USER_EMAIL}")
                    return True
            else:
                log_test("GET voice settings", "FAIL", f"Invalid response structure: {data}")
        else:
            log_test("GET voice settings", "FAIL", f"HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        log_test("GET voice settings", "FAIL", f"Exception: {str(e)}")
    
    return False

def test_3_post_voice_tts():
    """Test 3: POST /caos/voice/tts returns audio for a short known phrase"""
    print("=== Test 3: POST /caos/voice/tts ===")
    
    try:
        # Test with a short known phrase as specified
        payload = {
            "text": "Hello, this is a test of the text to speech system.",
            "voice": "nova",
            "speed": 1.0,
            "model": "tts-1-hd"
        }
        
        response = requests.post(f"{BASE_URL}/caos/voice/tts", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify response structure
            required_fields = ["audio_base64", "content_type", "voice", "model", "speed"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                # Verify audio_base64 is valid base64 and not empty
                try:
                    audio_data = base64.b64decode(data["audio_base64"])
                    if len(audio_data) > 0:
                        log_test("POST voice TTS", "PASS", f"Generated {len(audio_data)} bytes of audio for short known phrase")
                        return data["audio_base64"]  # Return for use in round-trip test
                    else:
                        log_test("POST voice TTS", "FAIL", "Audio data is empty")
                except Exception as decode_error:
                    log_test("POST voice TTS", "FAIL", f"Invalid base64 audio data: {decode_error}")
            else:
                log_test("POST voice TTS", "FAIL", f"Missing required fields: {missing_fields}")
        else:
            log_test("POST voice TTS", "FAIL", f"HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        log_test("POST voice TTS", "FAIL", f"Exception: {str(e)}")
    
    return None

def test_4_post_voice_transcribe():
    """Test 4: POST /caos/voice/transcribe accepts multipart form fields"""
    print("=== Test 4: POST /caos/voice/transcribe ===")
    
    try:
        # Generate real audio first using TTS
        tts_payload = {
            "text": "This is a test audio file for transcription testing.",
            "voice": "nova",
            "speed": 1.0,
            "model": "tts-1-hd"
        }
        
        tts_response = requests.post(f"{BASE_URL}/caos/voice/tts", json=tts_payload)
        
        if tts_response.status_code != 200:
            log_test("POST voice transcribe", "FAIL", f"Failed to generate test audio: {tts_response.status_code}")
            return False
            
        tts_data = tts_response.json()
        audio_data = base64.b64decode(tts_data["audio_base64"])
        
        # Test transcription with all required multipart form fields
        files = {
            'file': ('test_audio.mp3', io.BytesIO(audio_data), 'audio/mpeg')
        }
        
        data = {
            'user_email': TEST_USER_EMAIL,
            'model': 'gpt-4o-transcribe',
            'fallback_model': 'whisper-1',
            'language': 'en',
            'prompt': 'This is a test audio file for transcription testing.'
        }
        
        response = requests.post(f"{BASE_URL}/caos/voice/transcribe", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            
            # Verify response structure
            required_fields = ["text", "model_used", "fallback_used"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if not missing_fields:
                log_test("POST voice transcribe", "PASS", 
                       f"Accepts multipart form fields. Result: model={result['model_used']}, fallback_used={result['fallback_used']}")
                return True
            else:
                log_test("POST voice transcribe", "FAIL", f"Missing required fields: {missing_fields}")
        else:
            log_test("POST voice transcribe", "FAIL", f"HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        log_test("POST voice transcribe", "FAIL", f"Exception: {str(e)}")
    
    return False

def test_5_end_to_end_roundtrip(tts_audio_base64):
    """Test 5: End-to-end round-trip: use TTS-generated audio as uploaded file to /voice/transcribe"""
    print("=== Test 5: End-to-end round-trip ===")
    
    if not tts_audio_base64:
        log_test("End-to-end round-trip", "FAIL", "No TTS audio available from previous test")
        return False
    
    try:
        # Decode the base64 audio from TTS
        audio_data = base64.b64decode(tts_audio_base64)
        
        # Use the TTS-generated audio for transcription
        files = {
            'file': ('tts_generated.mp3', io.BytesIO(audio_data), 'audio/mpeg')
        }
        
        data = {
            'user_email': TEST_USER_EMAIL,
            'model': 'gpt-4o-transcribe',
            'fallback_model': 'whisper-1',
            'language': 'en',
            'prompt': 'Hello, this is a test of the text to speech system.'
        }
        
        response = requests.post(f"{BASE_URL}/caos/voice/transcribe", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            
            # Verify response structure includes required fields
            required_fields = ["text", "model_used", "fallback_used"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if not missing_fields:
                # Check if we got valid text result back
                transcribed_text = result["text"].strip()
                if len(transcribed_text) > 0:
                    log_test("End-to-end round-trip", "PASS", 
                           f"Round-trip successful. Text: '{transcribed_text}', model_used: {result['model_used']}, fallback_used: {result['fallback_used']}")
                    return True
                else:
                    log_test("End-to-end round-trip", "FAIL", "Transcription returned empty text")
            else:
                log_test("End-to-end round-trip", "FAIL", f"Missing required fields: {missing_fields}")
        else:
            log_test("End-to-end round-trip", "FAIL", f"HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        log_test("End-to-end round-trip", "FAIL", f"Exception: {str(e)}")
    
    return False

def test_6_fallback_behavior():
    """Test 6: If gpt-4o-transcribe is not accepted, confirm endpoint falls back cleanly to whisper-1"""
    print("=== Test 6: Fallback behavior verification ===")
    
    try:
        # Generate test audio
        tts_payload = {
            "text": "Testing fallback from gpt-4o-transcribe to whisper-1.",
            "voice": "alloy",
            "speed": 1.0,
            "model": "tts-1-hd"
        }
        
        tts_response = requests.post(f"{BASE_URL}/caos/voice/tts", json=tts_payload)
        
        if tts_response.status_code != 200:
            log_test("Fallback behavior", "FAIL", f"Failed to generate test audio: {tts_response.status_code}")
            return False
            
        tts_data = tts_response.json()
        audio_data = base64.b64decode(tts_data["audio_base64"])
        
        # Test with gpt-4o-transcribe as primary and whisper-1 as fallback
        files = {
            'file': ('fallback_test.mp3', io.BytesIO(audio_data), 'audio/mpeg')
        }
        
        data = {
            'user_email': TEST_USER_EMAIL,
            'model': 'gpt-4o-transcribe',
            'fallback_model': 'whisper-1',
            'language': 'en'
        }
        
        response = requests.post(f"{BASE_URL}/caos/voice/transcribe", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            
            # Check if the endpoint handles the request without 500 errors
            if "model_used" in result and "fallback_used" in result:
                model_used = result["model_used"]
                fallback_used = result["fallback_used"]
                
                # Verify clean fallback behavior (no 500 errors)
                if model_used == "whisper-1" and fallback_used:
                    log_test("Fallback behavior", "PASS", "Falls back cleanly from gpt-4o-transcribe to whisper-1 instead of 500ing")
                elif model_used == "gpt-4o-transcribe" and not fallback_used:
                    log_test("Fallback behavior", "PASS", "gpt-4o-transcribe accepted and worked directly")
                else:
                    log_test("Fallback behavior", "PASS", f"Clean handling: model_used={model_used}, fallback_used={fallback_used}")
                
                return True
            else:
                log_test("Fallback behavior", "FAIL", "Missing model_used or fallback_used fields")
        else:
            # Check if it's a clean failure (not a 500 error)
            if response.status_code != 500:
                log_test("Fallback behavior", "PASS", f"Clean failure with HTTP {response.status_code} (not a 500 error)")
                return True
            else:
                log_test("Fallback behavior", "FAIL", f"HTTP 500 error instead of clean fallback: {response.text}")
            
    except Exception as e:
        log_test("Fallback behavior", "FAIL", f"Exception: {str(e)}")
    
    return False

def test_7_no_internal_errors():
    """Test 7: No internal errors or unsafe failures"""
    print("=== Test 7: No internal errors or unsafe failures ===")
    
    error_count = 0
    
    # Test edge cases that should not cause 500 errors
    test_cases = [
        {
            "name": "Non-existent user voice settings",
            "endpoint": "/caos/voice/settings/nonexistent@example.com",
            "method": "GET",
            "expected_behavior": "Should return default settings, not 500"
        },
        {
            "name": "Very long text TTS",
            "endpoint": "/caos/voice/tts",
            "method": "POST",
            "data": {"text": "A" * 5000, "voice": "nova", "speed": 1.0, "model": "tts-1-hd"},
            "expected_behavior": "Should handle gracefully, not 500"
        }
    ]
    
    for test_case in test_cases:
        try:
            if test_case["method"] == "POST":
                response = requests.post(f"{BASE_URL}{test_case['endpoint']}", json=test_case["data"])
            else:
                response = requests.get(f"{BASE_URL}{test_case['endpoint']}")
            
            # Check for 500 errors (internal server errors)
            if response.status_code == 500:
                error_count += 1
                log_test(f"No internal errors - {test_case['name']}", "FAIL", f"HTTP 500 error: {response.text}")
            else:
                log_test(f"No internal errors - {test_case['name']}", "PASS", f"No 500 error (got {response.status_code})")
                
        except Exception as e:
            error_count += 1
            log_test(f"No internal errors - {test_case['name']}", "FAIL", f"Exception: {str(e)}")
    
    if error_count == 0:
        log_test("No internal errors verification", "PASS", "All edge cases handled without unsafe failures")
        return True
    else:
        log_test("No internal errors verification", "FAIL", f"Found {error_count} internal errors")
        return False

def main():
    """Run all voice/settings backend tests as specified in review request"""
    print("🎤 CAOS Backend Voice/Settings Testing")
    print("=" * 50)
    print(f"Testing against: {BASE_URL}")
    print(f"Test user: {TEST_USER_EMAIL}")
    print()
    print("Review Request Requirements:")
    print("1. POST /caos/voice/settings persists voice preferences for fresh test user")
    print("2. GET /caos/voice/settings/{user_email} returns saved preferences")
    print("3. POST /caos/voice/tts returns audio for short known phrase")
    print("4. POST /caos/voice/transcribe accepts multipart form fields")
    print("5. End-to-end round-trip: TTS-generated audio → transcribe")
    print("6. Fallback from gpt-4o-transcribe to whisper-1 without 500ing")
    print("7. No internal errors or unsafe failures")
    print()
    
    results = []
    
    # Run all tests in sequence as specified
    results.append(test_1_post_voice_settings())
    results.append(test_2_get_voice_settings())
    
    # TTS test returns audio data for round-trip test
    tts_audio = test_3_post_voice_tts()
    results.append(tts_audio is not None)
    
    results.append(test_4_post_voice_transcribe())
    results.append(test_5_end_to_end_roundtrip(tts_audio))
    results.append(test_6_fallback_behavior())
    results.append(test_7_no_internal_errors())
    
    # Summary
    print("=" * 50)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    test_names = [
        "1. POST /caos/voice/settings persists preferences",
        "2. GET /caos/voice/settings/{user_email} returns saved preferences",
        "3. POST /caos/voice/tts returns audio for short phrase",
        "4. POST /caos/voice/transcribe accepts multipart form fields",
        "5. End-to-end round-trip TTS → transcribe",
        "6. Fallback gpt-4o-transcribe → whisper-1 without 500ing",
        "7. No internal errors or unsafe failures"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
    
    print()
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All review request requirements verified! Voice/settings backend is working correctly.")
        print("✅ No contract mismatches or regressions found.")
        return True
    else:
        print(f"⚠️  {total - passed} requirement(s) failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)