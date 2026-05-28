"""SYVREN backend tests - auth + scoped chat + streaming.

Covers:
- /api/auth/me  (401 without token, 200 with Bearer)
- /api/auth/logout
- /api/chat/sessions  (CRUD scoped to user)
- /api/chat/sessions/{id}/messages  (404 on other user's session)
- /api/chat/sessions/{id}/stream  (SSE: user -> chunks -> done; 401 without token)
- MongoDB indexes ensured on startup
"""
import os
import json
import time
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # Fallback: read frontend .env at runtime
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

DEMO_TOKEN = "demo_token_123"
DEMO_USER_ID = "demo-user"
OTHER_TOKEN = f"test_token_{uuid.uuid4().hex[:8]}"
OTHER_USER_ID = f"test-user-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    db = c[DB_NAME]
    # Seed a "other user" + session
    db.users.insert_one({
        "user_id": OTHER_USER_ID,
        "email": f"TEST_{OTHER_USER_ID}@example.com",
        "name": "Other Test User",
        "picture": None,
    })
    from datetime import datetime, timezone, timedelta
    db.user_sessions.insert_one({
        "user_id": OTHER_USER_ID,
        "session_token": OTHER_TOKEN,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc),
    })
    yield db
    # Cleanup
    db.users.delete_one({"user_id": OTHER_USER_ID})
    db.user_sessions.delete_one({"session_token": OTHER_TOKEN})
    db.sessions.delete_many({"user_id": OTHER_USER_ID})
    db.sessions.delete_many({"user_id": DEMO_USER_ID, "title": {"$regex": "^TEST_"}})
    c.close()


@pytest.fixture
def demo_headers():
    return {"Authorization": f"Bearer {DEMO_TOKEN}"}


@pytest.fixture
def other_headers(mongo):  # depend on mongo so the test user/session is seeded
    return {"Authorization": f"Bearer {OTHER_TOKEN}"}


# ---------- AUTH ----------
class TestAuth:
    def test_me_without_token_401(self):
        r = requests.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401, r.text

    def test_me_with_bearer(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=demo_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user_id"] == DEMO_USER_ID
        assert data["email"] == "demo@syvren.app"
        assert "name" in data

    def test_me_invalid_token_401(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": "Bearer bogus_xyz"})
        assert r.status_code == 401

    def test_google_session_invalid_id_returns_401_or_502(self):
        # Random session_id should fail at upstream Emergent auth proxy.
        r = requests.post(f"{BASE_URL}/api/auth/google-session", json={"session_id": "not-a-real-id"})
        assert r.status_code in (401, 502), r.text


# ---------- CHAT SESSIONS SCOPING ----------
class TestChatSessions:
    def test_list_without_token_401(self):
        r = requests.get(f"{BASE_URL}/api/chat/sessions")
        assert r.status_code == 401

    def test_create_and_list(self, demo_headers):
        r = requests.post(f"{BASE_URL}/api/chat/sessions", headers=demo_headers)
        assert r.status_code == 200, r.text
        s = r.json()
        assert s["user_id"] == DEMO_USER_ID
        assert "id" in s
        sid = s["id"]

        # List should include it
        r2 = requests.get(f"{BASE_URL}/api/chat/sessions", headers=demo_headers)
        assert r2.status_code == 200
        ids = [x["id"] for x in r2.json()]
        assert sid in ids
        # all sessions belong to demo user
        assert all(x["user_id"] == DEMO_USER_ID for x in r2.json())

    def test_other_user_cannot_see_demo_sessions(self, demo_headers, other_headers):
        # Create on demo
        sid = requests.post(f"{BASE_URL}/api/chat/sessions", headers=demo_headers).json()["id"]
        # Other user lists -> shouldn't contain it
        r = requests.get(f"{BASE_URL}/api/chat/sessions", headers=other_headers)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert sid not in ids

    def test_get_messages_on_other_users_session_404(self, demo_headers, other_headers):
        sid = requests.post(f"{BASE_URL}/api/chat/sessions", headers=demo_headers).json()["id"]
        r = requests.get(f"{BASE_URL}/api/chat/sessions/{sid}/messages", headers=other_headers)
        assert r.status_code == 404

    def test_delete_only_owner(self, demo_headers, other_headers):
        sid = requests.post(f"{BASE_URL}/api/chat/sessions", headers=demo_headers).json()["id"]
        # Other tries to delete -> deleted_count=0, demo still sees it
        r = requests.delete(f"{BASE_URL}/api/chat/sessions/{sid}", headers=other_headers)
        assert r.status_code == 200  # endpoint returns {ok:true} even if not owned
        # Confirm session still exists for demo
        r2 = requests.get(f"{BASE_URL}/api/chat/sessions", headers=demo_headers)
        assert sid in [x["id"] for x in r2.json()]
        # Owner deletes
        r3 = requests.delete(f"{BASE_URL}/api/chat/sessions/{sid}", headers=demo_headers)
        assert r3.status_code == 200
        # gone
        r4 = requests.get(f"{BASE_URL}/api/chat/sessions/{sid}/messages", headers=demo_headers)
        assert r4.status_code == 404


# ---------- NON-STREAMING MESSAGE ----------
class TestSendMessage:
    def test_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/chat/sessions/whatever/message", json={"content": "hi"})
        assert r.status_code == 401

    def test_send_message_authenticated(self, demo_headers):
        sid = requests.post(f"{BASE_URL}/api/chat/sessions", headers=demo_headers).json()["id"]
        r = requests.post(
            f"{BASE_URL}/api/chat/sessions/{sid}/message",
            json={"content": "¿Qué es el teorema de Pitágoras?", "language": "es"},
            headers=demo_headers,
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "user_message" in data and "assistant_message" in data and "session" in data
        assert data["assistant_message"]["role"] == "assistant"
        assert len(data["assistant_message"]["content"]) > 10
        assert data["session"]["user_id"] == DEMO_USER_ID


# ---------- STREAMING ----------
class TestStreaming:
    def test_stream_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/chat/sessions/anything/stream", json={"content": "hi"})
        assert r.status_code == 401

    def test_stream_emits_user_chunks_done(self, demo_headers):
        sid = requests.post(f"{BASE_URL}/api/chat/sessions", headers=demo_headers).json()["id"]
        events = []
        with requests.post(
            f"{BASE_URL}/api/chat/sessions/{sid}/stream",
            json={"content": "Suma 2 + 3 paso a paso.", "language": "es"},
            headers=demo_headers,
            stream=True,
            timeout=60,
        ) as r:
            assert r.status_code == 200, r.text
            ctype = r.headers.get("content-type", "")
            assert "text/event-stream" in ctype, ctype
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if raw.startswith("data: "):
                    try:
                        evt = json.loads(raw[6:])
                    except Exception:
                        continue
                    events.append(evt)
                    if evt.get("type") == "done":
                        break
        types = [e["type"] for e in events]
        assert types[0] == "user", types
        assert "chunk" in types, types
        assert types[-1] == "done", types
        done = [e for e in events if e["type"] == "done"][0]
        assert "assistant" in done and done["assistant"]["role"] == "assistant"
        assert "session" in done and done["session"]["user_id"] == DEMO_USER_ID
        assert len(done["assistant"]["content"]) > 10


# ---------- INDEXES ----------
class TestIndexes:
    def test_mongo_indexes_present(self, mongo):
        # users.email unique
        info = mongo.users.index_information()
        email_idx = [v for k, v in info.items() if v["key"] == [("email", 1)]]
        assert email_idx and email_idx[0].get("unique") is True
        # user_sessions.session_token unique
        info2 = mongo.user_sessions.index_information()
        st_idx = [v for k, v in info2.items() if v["key"] == [("session_token", 1)]]
        assert st_idx and st_idx[0].get("unique") is True
        # user_sessions.expires_at TTL
        ttl_idx = [v for k, v in info2.items() if v["key"] == [("expires_at", 1)]]
        assert ttl_idx and ttl_idx[0].get("expireAfterSeconds") == 0


# ---------- LOGOUT ----------
class TestLogout:
    def test_logout_clears_session(self, mongo):
        # Create disposable session
        from datetime import datetime, timezone, timedelta
        tok = f"test_logout_{uuid.uuid4().hex[:8]}"
        mongo.user_sessions.insert_one({
            "user_id": DEMO_USER_ID,
            "session_token": tok,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "created_at": datetime.now(timezone.utc),
        })
        # /me works
        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        # logout
        r2 = requests.post(f"{BASE_URL}/api/auth/logout", headers={"Authorization": f"Bearer {tok}"})
        assert r2.status_code == 200
        # /me fails
        r3 = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert r3.status_code == 401
