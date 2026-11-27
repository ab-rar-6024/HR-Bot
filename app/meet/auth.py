import hashlib
import hmac
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from ..db import connect

COOKIE = "vo_session"
SESSION_HOURS = 12
_fails: dict[str, list[float]] = {}


def hash_pw(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${h.hex()}"


def check_pw(pw: str, stored: str) -> bool:
    try:
        _, salt, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(got.hex(), h)
    except Exception:
        return False


def create_user(email: str, name: str, role: str, password: str, must_change: bool = False) -> str:
    uid = str(uuid.uuid4())
    with connect() as c:
        c.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?)",
                  (uid, email.lower().strip(), name, role, hash_pw(password), int(must_change),
                   datetime.now(timezone.utc).isoformat()))
    return uid


def get_user_by_email(email: str):
    with connect() as c:
        return c.execute("SELECT * FROM users WHERE email=?", (email.lower().strip(),)).fetchone()


def _throttle(key: str):
    now = time.time()
    recent = [t for t in _fails.get(key, []) if now - t < 60]
    _fails[key] = recent
    if len(recent) >= 5:
        raise HTTPException(429, "Too many failed attempts. Wait a minute.")


def login(email: str, password: str, ip: str):
    key = f"{ip}|{email.lower()}"
    _throttle(key)
    u = get_user_by_email(email)
    # Always run a hash so response time doesn't reveal whether the account exists.
    ok = check_pw(password, u["pw_hash"] if u else hash_pw("x"))
    if not (u and ok):
        _fails.setdefault(key, []).append(time.time())
        raise HTTPException(401, "Invalid email or password")
    token = secrets.token_urlsafe(32)
    exp = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat()
    with connect() as c:
        c.execute("INSERT INTO sessions VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), u["id"], exp))
    return token, u


def user_from_token(token: str | None):
    if not token:
        return None
    with connect() as c:
        r = c.execute("SELECT u.*, s.expires_utc FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?",
                      (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if not r or r["expires_utc"] < datetime.now(timezone.utc).isoformat():
        return None
    return r


def logout(token: str | None):
    if token:
        with connect() as c:
            c.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))


def current_user(request: Request):
    u = user_from_token(request.cookies.get(COOKIE))
    if not u:
        raise HTTPException(401, "Not logged in")
    return u


def require_hr(request: Request):
    u = current_user(request)
    if u["role"] != "hr":
        raise HTTPException(403, "HR only")
    return u


def same_origin(request: Request):
    """CSRF guard for state-changing calls: Origin (when sent) must match Host."""
    origin = request.headers.get("origin")
    if origin and origin.split("://", 1)[-1] != request.headers.get("host"):
        raise HTTPException(403, "Cross-origin request blocked")
