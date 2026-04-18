"""CAOS API tests for files/links/voice endpoints and baseline chat regression."""

import io
import os
import uuid
import wave

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="session")
def api_client():
    """Shared HTTP client using public preview URL."""
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    session = requests.Session()
    return session


@pytest.fixture
def test_identity():
    """Unique test identity for isolated records."""
    token = uuid.uuid4().hex[:10]
    return {
        "email": f"TEST_caos_files_voice_{token}@example.com",
        "title": f"TEST files voice {token}",
        "token": token,
    }


def _create_silent_wav_bytes(seconds: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Generate a minimal valid WAV payload for transcription endpoint."""
    frame_count = int(seconds * sample_rate)
    pcm_silence = b"\x00\x00" * frame_count
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_silence)
    return buffer.getvalue()


# Module: files upload/download + list persistence
def test_upload_file_returns_downloadable_record_and_persists(api_client, test_identity):
    upload_url = f"{BASE_URL.rstrip('/')}/api/caos/files/upload"
    file_payload = io.BytesIO(b"TEST file upload bytes for CAOS")
    files = {"file": (f"TEST_{test_identity['token']}.txt", file_payload, "text/plain")}
    form_data = {"user_email": test_identity["email"]}

    response = api_client.post(upload_url, data=form_data, files=files, timeout=30)
    assert response.status_code == 200
    created = response.json()
    assert created["user_email"] == test_identity["email"]
    assert created["kind"] == "file"
    assert created["name"].startswith("TEST_")
    assert created["size"] > 0
    assert isinstance(created["id"], str)
    assert created["url"] == f"/api/caos/files/{created['id']}/download"

    list_response = api_client.get(
        f"{BASE_URL.rstrip('/')}/api/caos/files",
        params={"user_email": test_identity["email"]},
        timeout=30,
    )
    assert list_response.status_code == 200
    records = list_response.json()
    matched = next((item for item in records if item["id"] == created["id"]), None)
    assert matched is not None
    assert matched["name"] == created["name"]
    assert matched["kind"] == "file"

    download_response = api_client.get(f"{BASE_URL.rstrip('/')}{created['url']}", timeout=30)
    assert download_response.status_code == 200
    assert len(download_response.content) == created["size"]


# Module: link save + list persistence
def test_save_link_creates_link_record_and_lists(api_client, test_identity):
    payload = {
        "user_email": test_identity["email"],
        "url": f"https://example.com/{test_identity['token']}",
        "label": f"TEST Link {test_identity['token']}",
    }
    response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/files/link", json=payload, timeout=30)
    assert response.status_code == 200
    link = response.json()
    assert link["user_email"] == test_identity["email"]
    assert link["kind"] == "link"
    assert link["url"] == payload["url"]
    assert link["name"] == payload["label"]
    assert link["size"] == 0

    list_response = api_client.get(
        f"{BASE_URL.rstrip('/')}/api/caos/files",
        params={"user_email": test_identity["email"], "kind": "link"},
        timeout=30,
    )
    assert list_response.status_code == 200
    records = list_response.json()
    matched = next((item for item in records if item["id"] == link["id"]), None)
    assert matched is not None
    assert matched["name"] == payload["label"]
    assert matched["url"] == payload["url"]


# Module: link download rejection behavior
def test_link_download_returns_400(api_client, test_identity):
    create_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/files/link",
        json={
            "user_email": test_identity["email"],
            "url": "https://example.com/no-download",
            "label": "TEST no-download link",
        },
        timeout=30,
    )
    assert create_response.status_code == 200
    created = create_response.json()

    download_response = api_client.get(
        f"{BASE_URL.rstrip('/')}/api/caos/files/{created['id']}/download", timeout=30
    )
    assert download_response.status_code == 400
    assert "Links do not have downloadable files" in download_response.json().get("detail", "")


# Module: voice text-to-speech integration
def test_voice_tts_returns_base64_audio_payload(api_client):
    response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/voice/tts",
        json={
            "text": "TEST read this aloud from CAOS backend",
            "voice": "nova",
            "model": "tts-1-hd",
            "speed": 1.0,
        },
        timeout=90,
    )
    if response.status_code in (401, 403):
        pytest.skip(f"Voice TTS auth unavailable in preview env: {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("audio_base64"), str)
    assert len(data["audio_base64"]) > 16
    assert data["content_type"] == "audio/mpeg"
    assert data["voice"] == "nova"


# Module: voice speech-to-text integration
def test_voice_transcribe_accepts_upload_and_returns_text(api_client):
    wav_bytes = _create_silent_wav_bytes()
    files = {"file": ("TEST_transcribe.wav", io.BytesIO(wav_bytes), "audio/wav")}
    response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/voice/transcribe",
        files=files,
        timeout=90,
    )
    if response.status_code in (401, 403):
        pytest.skip(f"Voice transcription auth unavailable in preview env: {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert isinstance(data["text"], str)


# Module: baseline chat/session/artifacts regression after file+voice additions
def test_chat_session_artifacts_flow_still_operational(api_client, test_identity):
    upsert_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST files+voice user"},
        timeout=30,
    )
    assert upsert_response.status_code == 200

    session_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": test_identity["title"]},
        timeout=30,
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    chat_payload = {
        "user_email": test_identity["email"],
        "session_id": session_id,
        "content": "TEST please summarize this brief note for regression coverage",
    }
    first_attempt = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=90)
    response = first_attempt
    if first_attempt.status_code >= 500:
        response = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=chat_payload, timeout=90)
    assert response.status_code == 200
    turn = response.json()
    assert turn["session_id"] == session_id
    assert isinstance(turn.get("reply"), str)
    assert len(turn["reply"]) > 0

    messages_response = api_client.get(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_id}/messages", timeout=30
    )
    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert any(msg["role"] == "assistant" and isinstance(msg["content"], str) and msg["content"] for msg in messages)

    artifacts_response = api_client.get(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_id}/artifacts", timeout=30
    )
    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()
    assert isinstance(artifacts.get("receipts"), list)
    assert isinstance(artifacts.get("summaries"), list)
    assert isinstance(artifacts.get("seeds"), list)
