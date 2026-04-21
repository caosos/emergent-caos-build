"""Iteration 17 — PATCH/DELETE session CRUD + /api/admin/docs endpoints."""
import os
import subprocess
import json
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to env file
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


def _seed():
    """Run seed helper and return {admin_token, regular_token}."""
    result = subprocess.run(
        ["python", "/app/test_reports/seed_sessions.py"],
        capture_output=True, text=True, check=True,
        env={**os.environ},
    )
    # last line is the JSON
    for line in reversed(result.stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise RuntimeError(f"Seed failed: {result.stdout}\n{result.stderr}")


@pytest.fixture(scope="module")
def tokens():
    return _seed()


@pytest.fixture(scope="module")
def admin_headers(tokens):
    return {"Authorization": f"Bearer {tokens['admin_token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def regular_headers(tokens):
    return {"Authorization": f"Bearer {tokens['regular_token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_email():
    return "mytaxicloud@gmail.com"


def _get_regular_email(tokens):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {tokens['regular_token']}"})
    r.raise_for_status()
    return r.json().get("email")


def _create_session(headers, user_email, title="TEST_iter17_session"):
    payload = {"user_email": user_email, "title": title, "lane": "general"}
    r = requests.post(f"{BASE_URL}/api/caos/sessions", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# ----- PATCH /api/caos/sessions/{id} -----
class TestSessionPatch:
    def test_patch_requires_auth(self, admin_headers, admin_email):
        s = _create_session(admin_headers, admin_email)
        r = requests.patch(f"{BASE_URL}/api/caos/sessions/{s['session_id']}", json={"title": "x"})
        assert r.status_code == 401

    def test_patch_forbidden_for_other_user(self, admin_headers, regular_headers, admin_email):
        s = _create_session(admin_headers, admin_email)
        r = requests.patch(
            f"{BASE_URL}/api/caos/sessions/{s['session_id']}",
            headers=regular_headers, json={"title": "hijack"},
        )
        assert r.status_code == 403

    def test_patch_updates_title_and_flag(self, admin_headers, admin_email):
        s = _create_session(admin_headers, admin_email)
        r = requests.patch(
            f"{BASE_URL}/api/caos/sessions/{s['session_id']}",
            headers=admin_headers,
            json={"title": "TEST_renamed", "is_flagged": True, "lane": "focus"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["title"] == "TEST_renamed"
        assert data["is_flagged"] is True
        assert data["lane"] == "focus"
        assert data["session_id"] == s["session_id"]

    def test_patch_404_missing(self, admin_headers):
        r = requests.patch(
            f"{BASE_URL}/api/caos/sessions/nonexistent-{uuid.uuid4().hex}",
            headers=admin_headers, json={"title": "x"},
        )
        assert r.status_code == 404


# ----- DELETE /api/caos/sessions/{id} -----
class TestSessionDelete:
    def test_delete_requires_auth(self, admin_headers, admin_email):
        s = _create_session(admin_headers, admin_email)
        r = requests.delete(f"{BASE_URL}/api/caos/sessions/{s['session_id']}")
        assert r.status_code == 401

    def test_delete_forbidden_for_other_user(self, admin_headers, regular_headers, admin_email):
        s = _create_session(admin_headers, admin_email)
        r = requests.delete(
            f"{BASE_URL}/api/caos/sessions/{s['session_id']}", headers=regular_headers
        )
        assert r.status_code == 403

    def test_delete_cascades_messages(self, admin_headers, admin_email):
        s = _create_session(admin_headers, admin_email)
        # add a message
        mr = requests.post(
            f"{BASE_URL}/api/caos/messages",
            headers=admin_headers,
            json={"session_id": s["session_id"], "role": "user", "content": "TEST hello"},
        )
        assert mr.status_code == 200, mr.text

        # delete
        dr = requests.delete(
            f"{BASE_URL}/api/caos/sessions/{s['session_id']}", headers=admin_headers
        )
        assert dr.status_code == 200, dr.text
        body = dr.json()
        assert body == {"session_id": s["session_id"], "deleted": True}

        # messages gone
        mr2 = requests.get(
            f"{BASE_URL}/api/caos/sessions/{s['session_id']}/messages", headers=admin_headers
        )
        assert mr2.status_code == 200
        assert mr2.json() == []


# ----- GET /api/admin/docs -----
class TestAdminDocs:
    def test_list_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/docs")
        assert r.status_code == 401

    def test_list_forbidden_non_admin(self, regular_headers):
        r = requests.get(f"{BASE_URL}/api/admin/docs", headers=regular_headers)
        assert r.status_code == 403, r.text

    def test_list_admin_success(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/docs", headers=admin_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "documents" in data
        files = [d["filename"] for d in data["documents"]]
        assert any(f.endswith(".md") for f in files)
        # Blueprint files mentioned in review_request
        # (not strictly required so we just sanity-check format)
        for d in data["documents"]:
            assert "filename" in d and d["filename"].endswith(".md")
            assert "title" in d
            assert "size_bytes" in d

    def test_read_doc_admin(self, admin_headers):
        lst = requests.get(f"{BASE_URL}/api/admin/docs", headers=admin_headers).json()
        assert lst["documents"], "no docs available"
        target = lst["documents"][0]["filename"]
        r = requests.get(f"{BASE_URL}/api/admin/docs/{target}", headers=admin_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["filename"] == target
        assert isinstance(body["content"], str) and len(body["content"]) > 0

    def test_read_doc_non_admin_403(self, regular_headers):
        r = requests.get(f"{BASE_URL}/api/admin/docs/PRD.md", headers=regular_headers)
        assert r.status_code == 403

    def test_read_doc_missing_404(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/docs/does_not_exist_{uuid.uuid4().hex}.md", headers=admin_headers)
        assert r.status_code == 404

    def test_path_traversal_slash(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/docs/..%2Fetc%2Fpasswd", headers=admin_headers)
        # Server will URL-decode; '/' in filename triggers 400
        assert r.status_code in (400, 404)

    def test_path_traversal_dot_prefix(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/docs/.hidden", headers=admin_headers)
        assert r.status_code == 400

    def test_path_traversal_backslash(self, admin_headers):
        # backslash (url-encoded)
        r = requests.get(f"{BASE_URL}/api/admin/docs/bad%5Cname.md", headers=admin_headers)
        assert r.status_code == 400
