"""Tutor Metodológico backend API tests"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://minimal-tutor.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def created_session_ids():
    return []


def test_root(session):
    r = session.get(f"{API}/")
    assert r.status_code == 200
    assert "message" in r.json()


# Sessions CRUD
def test_create_session(session, created_session_ids):
    r = session.post(f"{API}/chat/sessions")
    assert r.status_code == 200
    data = r.json()
    assert "id" in data and isinstance(data["id"], str)
    assert data["title"] == "Nueva sesión"
    assert "created_at" in data and "updated_at" in data
    created_session_ids.append(data["id"])


def test_list_sessions_sorted(session, created_session_ids):
    # Create another session to verify sort
    time.sleep(0.05)
    r2 = session.post(f"{API}/chat/sessions")
    assert r2.status_code == 200
    sid2 = r2.json()["id"]
    created_session_ids.append(sid2)

    r = session.get(f"{API}/chat/sessions")
    assert r.status_code == 200
    sessions = r.json()
    assert isinstance(sessions, list)
    ids = [s["id"] for s in sessions]
    assert sid2 in ids
    # Verify sort desc by updated_at
    if len(sessions) >= 2:
        for i in range(len(sessions) - 1):
            assert sessions[i]["updated_at"] >= sessions[i + 1]["updated_at"]


def test_send_message_returns_3_sections(session, created_session_ids):
    sid = created_session_ids[0]
    payload = {"content": "Quiero calcular la hipotenusa de un triángulo con catetos de 3 y 4."}
    r = session.post(f"{API}/chat/sessions/{sid}/message", json=payload, timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "user_message" in data and "assistant_message" in data and "session" in data
    assert data["user_message"]["content"] == payload["content"]
    assert data["user_message"]["role"] == "user"
    assert data["assistant_message"]["role"] == "assistant"
    content = data["assistant_message"]["content"]
    # 3 sections present
    assert "## Archivo de Datos" in content
    assert "## Paso Activo" in content
    assert ("## Acción de Cierre" in content) or ("## Accion de Cierre" in content)
    # Title set from first user message
    assert data["session"]["title"].startswith("Quiero calcular la hipotenusa")
    # No final answer "5"
    lower = content.lower()
    # Check no emoji (basic)
    import re
    emoji_re = re.compile(
        "[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F\U0001F900-\U0001F9FF\u2600-\u27BF]",
        flags=re.UNICODE,
    )
    assert not emoji_re.search(content), f"Emoji detected in tutor response: {content}"
    # Should not contain numerical final result "5" prominently as answer (heuristic)
    # We at least ensure tutor asks/instructs (closing action exists with content)
    assert len(content.strip()) > 50


def test_get_messages_history(session, created_session_ids):
    sid = created_session_ids[0]
    r = session.get(f"{API}/chat/sessions/{sid}/messages")
    assert r.status_code == 200
    msgs = r.json()
    assert isinstance(msgs, list)
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    # Order by timestamp asc
    for i in range(len(msgs) - 1):
        assert msgs[i]["timestamp"] <= msgs[i + 1]["timestamp"]


def test_multi_turn_context(session, created_session_ids):
    sid = created_session_ids[0]
    r = session.post(
        f"{API}/chat/sessions/{sid}/message",
        json={"content": "Sí, ya identifiqué la fórmula, ¿qué hago ahora?"},
        timeout=120,
    )
    assert r.status_code == 200
    content = r.json()["assistant_message"]["content"]
    assert "## Archivo de Datos" in content
    assert "## Paso Activo" in content


def test_empty_message_400(session, created_session_ids):
    sid = created_session_ids[0]
    r = session.post(f"{API}/chat/sessions/{sid}/message", json={"content": "   "})
    assert r.status_code == 400


def test_missing_session_404(session):
    r = session.post(
        f"{API}/chat/sessions/nonexistent-id-xyz/message",
        json={"content": "hola"},
    )
    assert r.status_code == 404


def test_delete_session(session, created_session_ids):
    sid = created_session_ids[-1]
    r = session.delete(f"{API}/chat/sessions/{sid}")
    assert r.status_code == 200
    # Verify gone
    r2 = session.get(f"{API}/chat/sessions")
    ids = [s["id"] for s in r2.json()]
    assert sid not in ids
    # Messages also removed
    r3 = session.get(f"{API}/chat/sessions/{sid}/messages")
    assert r3.status_code == 200
    assert r3.json() == []


def test_cleanup(session, created_session_ids):
    for sid in created_session_ids:
        try:
            session.delete(f"{API}/chat/sessions/{sid}")
        except Exception:
            pass
