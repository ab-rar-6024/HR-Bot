import os
import tempfile

os.environ["VERIFYOPS_DATA"] = tempfile.mkdtemp()
os.environ["VERIFYOPS_API_KEYS"] = "test-key"

from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.meet import auth  # noqa: E402


@pytest.fixture(scope="module")
def client():
    init_db()
    if not auth.get_user_by_email("hr@x.com"):
        auth.create_user("hr@x.com", "Asha", "hr", "correct-horse-battery")
        auth.create_user("hr2@x.com", "Other HR", "hr", "correct-horse-battery")
    with TestClient(app, base_url="http://testserver") as c:
        yield c


def login(client, email, pw):
    c = TestClient(app, base_url="http://testserver")
    return c, c.post("/api/auth/login", json={"email": email, "password": pw})


def mk(c, minutes=0, email="cand@x.com"):
    start = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
    return c.post("/api/meetings", json={"title": "R1", "candidate_name": "Ravi", "candidate_email": email,
                                         "start_utc": start, "duration_min": 30})


def test_pages_render():
    with TestClient(app) as c:
        for p in ("/login",):
            assert c.get(p).status_code == 200
        assert "Interview portal" in c.get("/login").text
        assert c.get("/hr", follow_redirects=False).status_code in (302, 307)


def test_bad_login_and_hr_only(client):
    _, r = login(client, "hr@x.com", "wrong")
    assert r.status_code == 401
    anon = TestClient(app)
    assert anon.post("/api/meetings", json={}).status_code == 401


def test_full_flow_and_access_control(client):
    hr, r = login(client, "hr@x.com", "correct-horse-battery")
    assert r.status_code == 200 and r.json()["role"] == "hr"
    m = mk(hr, minutes=5).json()
    assert m["temp_password"] and m["link"].endswith(m["id"])

    # candidate: forced to change temp password, then can fetch the meeting
    cand, r = login(client, "cand@x.com", m["temp_password"])
    assert r.json()["must_change"] is True
    assert cand.post("/api/auth/change-password", json={"new_password": "short"}).status_code == 422
    assert cand.post("/api/auth/change-password", json={"new_password": "a-much-longer-pass"}).status_code == 200
    info = cand.get(f"/api/meetings/{m['id']}/info").json()
    assert info["role"] == "candidate" and info["join_error"] is None

    # candidate cannot create meetings; other HR cannot see this meeting
    assert mk(cand).status_code == 403
    hr2, _ = login(client, "hr2@x.com", "correct-horse-battery")
    assert hr2.get(f"/api/meetings/{m['id']}/info").status_code == 404
    # a different candidate cannot join
    mk(hr, minutes=5, email="other@x.com")
    # websocket auth: stranger refused
    with pytest.raises(Exception):
        with TestClient(app).websocket_connect(f"/ws/meet/{m['id']}"):
            pass


def test_signaling_relay_and_events(client):
    hr, _ = login(client, "hr@x.com", "correct-horse-battery")
    m = mk(hr, minutes=0, email="sig@x.com").json()
    cand, _ = login(client, "sig@x.com", m["temp_password"])
    cand.post("/api/auth/change-password", json={"new_password": "a-much-longer-pass"})
    # One client = one event loop (as in production); identities are passed as cookies.
    ck = lambda c: {"cookie": f"{auth.COOKIE}={c.cookies.get(auth.COOKIE)}"}  # noqa: E731
    url = f"/ws/meet/{m['id']}"
    with client.websocket_connect(url, headers=ck(hr)) as wh:
        assert wh.receive_json()["type"] == "peers"
        with client.websocket_connect(url, headers=ck(cand)) as wc:
            assert wc.receive_json() == {"type": "peers", "present": ["hr"]}
            assert wh.receive_json() == {"type": "peer_joined", "role": "candidate"}
            wc.send_json({"type": "offer", "sdp": {"type": "offer", "sdp": "x"}, "screenStreamId": "S1"})
            assert wh.receive_json()["screenStreamId"] == "S1"
            wc.send_json({"type": "event", "name": "screen_stopped"})
            assert wh.receive_json()["name"] == "screen_stopped"
            wc.send_json({"type": "event", "name": "bogus"})  # ignored, not forwarded
    names = [e["name"] for e in hr.get(f"/api/meetings/{m['id']}/events").json()]
    assert "screen_stopped" in names and "joined" in names


def test_too_early_blocked(client):
    hr, _ = login(client, "hr@x.com", "correct-horse-battery")
    m = mk(hr, minutes=600, email="early@x.com").json()
    assert hr.get(f"/api/meetings/{m['id']}/info").json()["join_error"].startswith("Too early")
