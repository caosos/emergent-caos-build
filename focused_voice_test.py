#!/usr/bin/env python3
"""
CAOS Backend Voice/Settings Focused Testing Script
Focused testing to identify specific issues with voice endpoints.
"""

import base64
import io
import json
import requests
import tempfile
from pathlib import Path

# Configuration
BASE_URL = "https://memory-hub-63.preview.emergentagent.com/api"
TEST_USER_EMAIL = "voice.test@emergentagent.com"

def log_test(test_name, status, details=""):
    """Log test results with consistent formatting"""
    status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{status_symbol} {test_name}: {status}")
    if details:
        print(f"   {details}")
    print()

def test_transcribe_with_real_audio():
    """Test transcription with TTS-generated audio"""
    print("=== Testing transcription with real audio ===")
    
    try:
        # First generate some audio with TTS
        tts_payload = {
            "text": "This is a test message for transcription.",
            "voice": "nova",
            "speed": 1.0,
            "model": "tts-1-hd"
        }
        
        tts_response = requests.post(f"{BASE_URL}/caos/voice/tts", json=tts_payload)
        
        if tts_response.status_code != 200:
            log_test("TTS for transcription test", "FAIL", f"TTS failed: {tts_response.status_code}")
            return False
            
        tts_data = tts_response.json()
        audio_data = base64.b64decode(tts_data["audio_base64"])
        
        # Now use this audio for transcription
        files = {
            'file': ('test_audio.mp3', io.BytesIO(audio_data), 'audio/mpeg')
        }
        
        data = {
            'user_email': TEST_USER_EMAIL,
            'model': 'gpt-4o-transcribe',
            'fallback_model': 'whisper-1',
            'language': 'en',
            'prompt': 'This is a test message for transcription.'
        }
        
        response = requests.post(f"{BASE_URL}/caos/voice/transcribe", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            log_test("Transcription with real audio", "PASS", 
                   f"Transcribed: '{result.get('text', '')}', Model: {result.get('model_used', '')}, Fallback: {result.get('fallback_used', '')}")
            return True
        else:
            log_test("Transcription with real audio", "FAIL", f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        log_test("Transcription with real audio", "FAIL", f"Exception: {str(e)}")
        return False

def test_transcribe_fallback_behavior():
    """Test fallback behavior specifically"""
    print("=== Testing fallback behavior ===")
    
    try:
        # Generate audio first
        tts_payload = {
            "text": "Testing fallback from gpt-4o-transcribe to whisper-1.",
            "voice": "alloy",
            "speed": 1.0,
            "model": "tts-1-hd"
        }
        
        tts_response = requests.post(f"{BASE_URL}/caos/voice/tts", json=tts_payload)
        
        if tts_response.status_code != 200:
            log_test("TTS for fallback test", "FAIL", f"TTS failed: {tts_response.status_code}")
            return False
            
        tts_data = tts_response.json()
        audio_data = base64.b64decode(tts_data["audio_base64"])
        
        # Test transcription with explicit models
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
            model_used = result.get('model_used', '')
            fallback_used = result.get('fallback_used', False)
            
            if model_used == 'whisper-1' and fallback_used:
                log_test("Fallback behavior", "PASS", "Successfully fell back from gpt-4o-transcribe to whisper-1")
            elif model_used == 'gpt-4o-transcribe' and not fallback_used:
                log_test("Fallback behavior", "PASS", "gpt-4o-transcribe worked directly")
            else:
                log_test("Fallback behavior", "WARNING", f"Unexpected: model_used={model_used}, fallback_used={fallback_used}")
            
            return True
        else:
            log_test("Fallback behavior", "FAIL", f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        log_test("Fallback behavior", "FAIL", f"Exception: {str(e)}")
        return False

def test_tts_edge_cases():
    """Test TTS with edge cases but valid parameters"""
    print("=== Testing TTS edge cases ===")
    
    test_cases = [
        {
            "name": "Very short text",
            "payload": {"text": "Hi", "voice": "nova", "speed": 1.0, "model": "tts-1-hd"}
        },
        {
            "name": "Different voice",
            "payload": {"text": "Testing with alloy voice", "voice": "alloy", "speed": 1.0, "model": "tts-1-hd"}
        },
        {
            "name": "Different speed",
            "payload": {"text": "Testing with faster speed", "voice": "nova", "speed": 1.5, "model": "tts-1-hd"}
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        try:
            response = requests.post(f"{BASE_URL}/caos/voice/tts", json=test_case["payload"])
            
            if response.status_code == 200:
                data = response.json()
                if "audio_base64" in data and len(data["audio_base64"]) > 0:
                    log_test(f"TTS {test_case['name']}", "PASS", f"Generated audio successfully")
                else:
                    log_test(f"TTS {test_case['name']}", "FAIL", "No audio data returned")
                    all_passed = False
            else:
                log_test(f"TTS {test_case['name']}", "FAIL", f"HTTP {response.status_code}: {response.text}")
                all_passed = False
                
        except Exception as e:
            log_test(f"TTS {test_case['name']}", "FAIL", f"Exception: {str(e)}")
            all_passed = False
    
    return all_passed

def test_voice_settings_persistence():
    """Test voice settings persistence with different configurations"""
    print("=== Testing voice settings persistence ===")
    
    test_configs = [
        {
            "name": "Configuration 1",
            "settings": {
                "user_email": TEST_USER_EMAIL,
                "stt_primary_model": "gpt-4o-transcribe",
                "stt_fallback_model": "whisper-1",
                "stt_language": "en",
                "tts_model": "tts-1-hd",
                "tts_voice": "nova",
                "tts_speed": 1.0
            }
        },
        {
            "name": "Configuration 2",
            "settings": {
                "user_email": TEST_USER_EMAIL,
                "stt_primary_model": "whisper-1",
                "stt_fallback_model": "whisper-1",
                "stt_language": "en",
                "tts_model": "tts-1-hd",
                "tts_voice": "alloy",
                "tts_speed": 1.2
            }
        }
    ]
    
    for config in test_configs:
        try:
            # Save settings
            post_response = requests.post(f"{BASE_URL}/caos/voice/settings", json=config["settings"])
            
            if post_response.status_code != 200:
                log_test(f"Save {config['name']}", "FAIL", f"HTTP {post_response.status_code}")
                continue
            
            # Retrieve settings
            get_response = requests.get(f"{BASE_URL}/caos/voice/settings/{TEST_USER_EMAIL}")
            
            if get_response.status_code != 200:
                log_test(f"Retrieve {config['name']}", "FAIL", f"HTTP {get_response.status_code}")
                continue
            
            retrieved_data = get_response.json()
            retrieved_prefs = retrieved_data.get("voice_preferences", {})
            
            # Verify all settings match
            all_match = True
            for key, expected_value in config["settings"].items():
                if key == "user_email":
                    continue  # Skip user_email as it's not in preferences
                
                if retrieved_prefs.get(key) != expected_value:
                    all_match = False
                    log_test(f"Verify {config['name']}", "FAIL", 
                           f"Mismatch in {key}: expected {expected_value}, got {retrieved_prefs.get(key)}")
                    break
            
            if all_match:
                log_test(f"Settings persistence {config['name']}", "PASS", "All settings saved and retrieved correctly")
            
        except Exception as e:
            log_test(f"Settings persistence {config['name']}", "FAIL", f"Exception: {str(e)}")
    
    return True

def main():
    """Run focused voice/settings tests"""
    print("🎤 CAOS Backend Voice/Settings Focused Testing")
    print("=" * 60)
    print(f"Testing against: {BASE_URL}")
    print(f"Test user: {TEST_USER_EMAIL}")
    print()
    
    # Run focused tests
    test_voice_settings_persistence()
    test_tts_edge_cases()
    test_transcribe_with_real_audio()
    test_transcribe_fallback_behavior()
    
    print("=" * 60)
    print("✅ Focused testing completed")

if __name__ == "__main__":
    main()