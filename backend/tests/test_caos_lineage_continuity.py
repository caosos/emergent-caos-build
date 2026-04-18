"""CAOS lineage and continuity regression tests for chat artifact chaining."""

import os
import uuid

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="session")
def api_client():
    """Shared HTTP client for public preview API calls."""
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return requests.Session()


@pytest.fixture
def test_identity():
    """Isolated user/session identity per test run."""
    token = uuid.uuid4().hex[:10]
    return {
        "email": f"TEST_caos_lineage_{token}@example.com",
        "title": f"TEST lineage {token}",
    }


def _chat_with_retry(api_client, payload):
    """Retry once for transient upstream LLM failures."""
    first = api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=payload, timeout=90)
    if first.status_code < 500:
        return first
    return api_client.post(f"{BASE_URL.rstrip('/')}/api/caos/chat", json=payload, timeout=90)


# Module: POST /api/caos/chat lineage persistence across receipt/summary/seed artifacts
def test_chat_persists_lineage_fields_across_artifacts(api_client, test_identity):
    profile_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST Lineage"},
        timeout=30,
    )
    assert profile_response.status_code == 200

    session_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": test_identity["title"]},
        timeout=30,
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    first_chat = _chat_with_retry(
        api_client,
        {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "TEST first lineage turn for continuity checks",
        },
    )
    assert first_chat.status_code == 200

    second_chat = _chat_with_retry(
        api_client,
        {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "TEST second lineage turn to enforce previous ids and depth increment",
        },
    )
    assert second_chat.status_code == 200

    artifacts_response = api_client.get(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_id}/artifacts",
        timeout=30,
    )
    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()

    receipts = artifacts.get("receipts", [])
    summaries = artifacts.get("summaries", [])
    seeds = artifacts.get("seeds", [])

    assert len(receipts) >= 2
    assert len(summaries) >= 2
    assert len(seeds) >= 2

    latest_receipt, previous_receipt = receipts[0], receipts[1]
    latest_summary, previous_summary = summaries[0], summaries[1]
    latest_seed, previous_seed = seeds[0], seeds[1]

    assert latest_receipt["lineage_depth"] == previous_receipt["lineage_depth"] + 1
    assert latest_summary["lineage_depth"] == previous_summary["lineage_depth"] + 1
    assert latest_seed["lineage_depth"] == previous_seed["lineage_depth"] + 1

    assert latest_receipt["previous_receipt_id"] == previous_receipt["id"]
    assert latest_receipt["previous_summary_id"] == previous_summary["id"]
    assert latest_receipt["previous_seed_id"] == previous_seed["id"]
    assert latest_summary["previous_summary_id"] == previous_summary["id"]
    assert latest_seed["previous_seed_id"] == previous_seed["id"]
    assert latest_seed["previous_summary_id"] == previous_summary["id"]

    assert isinstance(latest_receipt.get("source_message_ids"), list)
    assert len(latest_receipt["source_message_ids"]) == 2
    assert isinstance(latest_summary.get("source_message_ids"), list)
    assert len(latest_summary["source_message_ids"]) == 2
    assert isinstance(latest_seed.get("source_message_ids"), list)
    assert len(latest_seed["source_message_ids"]) == 2


# Module: GET /api/caos/sessions/{session_id}/continuity latest surfaces + lineage depth
def test_continuity_returns_latest_summary_seed_receipt_and_depth(api_client, test_identity):
    profile_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/profile/upsert",
        json={"user_email": test_identity["email"], "preferred_name": "TEST Continuity"},
        timeout=30,
    )
    assert profile_response.status_code == 200

    session_response = api_client.post(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions",
        json={"user_email": test_identity["email"], "title": f"{test_identity['title']} continuity"},
        timeout=30,
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    turn_one = _chat_with_retry(
        api_client,
        {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "TEST continuity turn one",
        },
    )
    assert turn_one.status_code == 200

    turn_two = _chat_with_retry(
        api_client,
        {
            "user_email": test_identity["email"],
            "session_id": session_id,
            "content": "TEST continuity turn two",
        },
    )
    assert turn_two.status_code == 200

    continuity_response = api_client.get(
        f"{BASE_URL.rstrip('/')}/api/caos/sessions/{session_id}/continuity",
        timeout=30,
    )
    assert continuity_response.status_code == 200
    continuity = continuity_response.json()

    assert continuity["session_id"] == session_id
    assert isinstance(continuity.get("lineage_depth"), int)
    assert continuity["lineage_depth"] >= 2

    assert isinstance(continuity.get("latest_receipt"), dict)
    assert isinstance(continuity.get("latest_summary"), dict)
    assert isinstance(continuity.get("latest_seed"), dict)

    latest_receipt = continuity["latest_receipt"]
    latest_summary = continuity["latest_summary"]
    latest_seed = continuity["latest_seed"]

    assert latest_receipt["session_id"] == session_id
    assert latest_summary["session_id"] == session_id
    assert latest_seed["session_id"] == session_id

    assert latest_receipt["lineage_depth"] == continuity["lineage_depth"]
    assert latest_summary["lineage_depth"] == continuity["lineage_depth"]
    assert latest_seed["lineage_depth"] == continuity["lineage_depth"]
