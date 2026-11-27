import json
import logging
import os
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from ..db import connect
from . import auth, pages

log = logging.getLogger("verifyops.meet")
router = APIRouter()

PUBLIC_URL = os.getenv("VERIFYOPS_PUBLIC_URL", "http://localhost:8000").rstrip("/")
ICE = [s.strip() for s in os.getenv("VERIFYOPS_ICE", "stun:stun.l.google.com:19302").split(",") if s.strip()]
TURN_USER, TURN_PASS = os.getenv("VERIFYOPS_TURN_USER"), os.getenv("VERIFYOPS_TURN_PASS")
JOIN_EARLY_MIN, JOIN_LATE_MIN = 15, 60


def now():
    return datetime.now(timezone.utc)


def log_event(mid: str, uid: str | None, name: str, detail: str = ""):
    with connect() as c:
        c.execute("INSERT INTO meeting_events VALUES (?,?,?,?,?)", (mid, uid, name, detail[:500], now().isoformat()))


# ---------- pages ----------
@router.get("/", response_class=HTMLResponse)
def root(request: Request):
    u = auth.user_from_token(request.cookies.get(auth.COOKIE))
    if not u:
        return RedirectResponse("/login")
    return RedirectResponse("/hr" if u["role"] == "hr" else "/my")


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return pages.LOGIN


@router.get("/hr", response_class=HTMLResponse)
def hr_page(request: Request):
    u = auth.user_from_token(request.cookies.get(auth.COOKIE))
    if not u or u["role"] != "hr":
        return RedirectResponse("/login?next=/hr")
    return pages.HR


@router.get("/my", response_class=HTMLResponse)
def my_page(request: Request):
    u = auth.user_from_token(request.cookies.get(auth.COOKIE))
    if not u:
        return RedirectResponse("/login?next=/my")
    return pages.MY


@router.get("/meet/{mid}", response_class=HTMLResponse)
def room_page(mid: str, request: Request):
    u = auth.user_from_token(request.cookies.get(auth.COOKIE))
    if not u:
        return RedirectResponse(f"/login?next=/meet/{mid}")
    return pages.ROOM


# ---------- auth API ----------
class LoginIn(BaseModel):
    email: str
    password: str


class ChangePwIn(BaseModel):
    new_password: str = Field(min_length=10, max_length=128)


@router.post("/api/auth/login", dependencies=[Depends(auth.same_origin)])
def api_login(body: LoginIn, request: Request, response: Response):
    token, u = auth.login(body.email, body.password, request.client.host if request.client else "?")
    response.set_cookie(auth.COOKIE, token, httponly=True, samesite="lax", max_age=auth.SESSION_HOURS * 3600,
                        secure=request.url.scheme == "https")
    return {"role": u["role"], "name": u["name"], "must_change": bool(u["must_change"])}


@router.post("/api/auth/logout", dependencies=[Depends(auth.same_origin)])
def api_logout(request: Request, response: Response):
    auth.logout(request.cookies.get(auth.COOKIE))
    response.delete_cookie(auth.COOKIE)
    return {"ok": True}


@router.post("/api/auth/change-password", dependencies=[Depends(auth.same_origin)])
def change_pw(body: ChangePwIn, u=Depends(auth.current_user)):
    with connect() as c:
        c.execute("UPDATE users SET pw_hash=?, must_change=0 WHERE id=?", (auth.hash_pw(body.new_password), u["id"]))
    return {"ok": True}


@router.get("/api/me")
def me(u=Depends(auth.current_user)):
    return {"id": u["id"], "name": u["name"], "email": u["email"], "role": u["role"], "must_change": bool(u["must_change"])}


# ---------- meetings API ----------
class MeetingIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    candidate_name: str = Field(min_length=1, max_length=120)
    candidate_email: EmailStr
    start_utc: datetime
    duration_min: int = Field(30, ge=5, le=240)


def _send_mail(to: str, subject: str, body: str) -> bool:
    resend_key = os.getenv("VERIFYOPS_RESEND_API_KEY")
    if resend_key:
        try:
            import httpx
            r = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}"},
                json={
                    "from": os.getenv("VERIFYOPS_SMTP_FROM", "ProofyX VerifyOps <onboarding@resend.dev>"),
                    "to": [to],
                    "subject": subject,
                    "text": body,
                },
                timeout=15,
            )
            if r.status_code < 300:
                return True
            log.warning("Resend email to %s failed (%s): %s", to, r.status_code, r.text)
        except Exception as e:
            log.warning("Resend email to %s failed: %s", to, e)
    host = os.getenv("VERIFYOPS_SMTP_HOST")
    if not host:
        return False
    try:
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = os.getenv("VERIFYOPS_SMTP_FROM", "no-reply@localhost"), to, subject
        m.set_content(body)
        with smtplib.SMTP(host, int(os.getenv("VERIFYOPS_SMTP_PORT", 587)), timeout=15) as s:
            s.starttls()
            if os.getenv("VERIFYOPS_SMTP_USER"):
                s.login(os.environ["VERIFYOPS_SMTP_USER"], os.environ["VERIFYOPS_SMTP_PASS"])
            s.send_message(m)
        return True
    except Exception as e:
        log.warning("email to %s failed: %s", to, e)
        return False


def _public_url(request: Request | None = None) -> str:
    env_url = os.getenv("VERIFYOPS_PUBLIC_URL", "").strip().rstrip("/")
    if env_url and "localhost" not in env_url and "127.0.0.1" not in env_url:
        return env_url
    if request is not None:
        fwd_proto = request.headers.get("x-forwarded-proto")
        fwd_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if fwd_host and not fwd_host.startswith(("localhost", "127.0.0.1")):
            proto = fwd_proto or request.url.scheme
            return f"{proto}://{fwd_host}".rstrip("/")
        return str(request.base_url).rstrip("/")
    return PUBLIC_URL


def _row(m, with_people=True, base_url: str | None = None):
    active = sorted(ROOMS.get(m["id"], {}).keys())
    base = (base_url or PUBLIC_URL).rstrip("/")
    d = {"id": m["id"], "title": m["title"], "start_utc": m["start_utc"], "duration_min": m["duration_min"],
         "cancelled": bool(m["cancelled"]), "link": f"{base}/meet/{m['id']}", "active_roles": active}
    if with_people:
        d["candidate_name"], d["candidate_email"] = m["cname"], m["cemail"]
        d["hr_name"] = m["hname"]
    return d


@router.post("/api/meetings", dependencies=[Depends(auth.same_origin)])
def create_meeting(body: MeetingIn, request: Request, hr=Depends(auth.require_hr)):
    if body.start_utc.tzinfo is None:
        raise HTTPException(422, "start_utc must include a timezone")
    cand = auth.get_user_by_email(body.candidate_email)
    temp_pw = None
    if cand and cand["role"] != "candidate":
        raise HTTPException(409, "That email belongs to an HR account")
    if not cand:
        temp_pw = secrets.token_urlsafe(9)
        cid = auth.create_user(body.candidate_email, body.candidate_name, "candidate", temp_pw, must_change=True)
    else:
        cid = cand["id"]
        if cand["must_change"]:
            temp_pw = secrets.token_urlsafe(9)
            with connect() as c:
                c.execute("UPDATE users SET pw_hash=? WHERE id=?", (auth.hash_pw(temp_pw), cid))
    mid = secrets.token_urlsafe(9)
    with connect() as c:
        c.execute("INSERT INTO meetings VALUES (?,?,?,?,?,?,?,0)",
                  (mid, body.title, hr["id"], cid, body.start_utc.astimezone(timezone.utc).isoformat(),
                   body.duration_min, now().isoformat()))
    link = f"{_public_url(request)}/meet/{mid}"
    when = body.start_utc.astimezone(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    text = (f"Hello {body.candidate_name},\n\nYou are invited to: {body.title}\nWhen: {when} ({body.duration_min} min)\n"
            f"Join: {link}\n\nSign in with {body.candidate_email}.")
    if temp_pw:
        text += f"\nTemporary password: {temp_pw} (you will be asked to change it)."
    else:
        text += "\nUse your existing account password to sign in."
    text += ("\n\nThis interview requires your camera, microphone and screen sharing. You will be shown exactly what is "
             "shared and must agree before joining.")
    emailed = _send_mail(body.candidate_email, f"Interview invitation: {body.title}", text)
    log_event(mid, hr["id"], "scheduled", body.candidate_email)
    return {"id": mid, "link": link, "emailed": emailed, "temp_password": temp_pw,
            "note": None if emailed else "SMTP not configured: share the link (and temporary password) with the candidate yourself."}


@router.get("/api/meetings")
def list_meetings(request: Request, u=Depends(auth.current_user)):
    col = "hr_id" if u["role"] == "hr" else "candidate_id"
    with connect() as c:
        rows = c.execute(f"""SELECT m.*, cu.name cname, cu.email cemail, hu.name hname FROM meetings m
            JOIN users cu ON cu.id=m.candidate_id JOIN users hu ON hu.id=m.hr_id
            WHERE m.{col}=? ORDER BY m.start_utc DESC LIMIT 200""", (u["id"],)).fetchall()
    base = _public_url(request)
    return [_row(r, base_url=base) for r in rows]


@router.delete("/api/meetings/{mid}", dependencies=[Depends(auth.same_origin)])
def cancel(mid: str, hr=Depends(auth.require_hr)):
    with connect() as c:
        n = c.execute("UPDATE meetings SET cancelled=1 WHERE id=? AND hr_id=?", (mid, hr["id"])).rowcount
    if not n:
        raise HTTPException(404, "Not found")
    log_event(mid, hr["id"], "cancelled")
    return {"ok": True}


def _meeting_for(mid: str, u):
    with connect() as c:
        m = c.execute("""SELECT m.*, cu.name cname, hu.name hname FROM meetings m
            JOIN users cu ON cu.id=m.candidate_id JOIN users hu ON hu.id=m.hr_id WHERE m.id=?""", (mid,)).fetchone()
    if not m or u["id"] not in (m["hr_id"], m["candidate_id"]):
        raise HTTPException(404, "Meeting not found")  # same answer for 'not yours' and 'doesn't exist'
    return m


def _window_error(m) -> str | None:
    if m["cancelled"]:
        return "This meeting was cancelled."
    start = datetime.fromisoformat(m["start_utc"])
    if now() < start - timedelta(minutes=JOIN_EARLY_MIN):
        return f"Too early. You can join from {(start - timedelta(minutes=JOIN_EARLY_MIN)).strftime('%H:%M UTC on %d %b')}."
    if now() > start + timedelta(minutes=m["duration_min"] + JOIN_LATE_MIN):
        return "This meeting has ended."
    return None


@router.get("/api/meetings/{mid}/info")
def meeting_info(mid: str, u=Depends(auth.current_user)):
    m = _meeting_for(mid, u)
    ice = [{"urls": ICE}] if ICE else []
    if TURN_USER and ICE:
        ice = [{"urls": [i for i in ICE if i.startswith("turn")], "username": TURN_USER, "credential": TURN_PASS},
               {"urls": [i for i in ICE if i.startswith("stun")]}]
    return {"id": mid, "title": m["title"], "role": u["role"], "me": u["name"],
            "other": m["cname"] if u["role"] == "hr" else m["hname"], "start_utc": m["start_utc"],
            "duration_min": m["duration_min"], "join_error": _window_error(m), "iceServers": ice,
            "must_change": bool(u["must_change"])}


# ---------- signaling ----------
ROOMS: dict[str, dict[str, WebSocket]] = {}
RELAY = {"offer", "answer", "ice", "bye"}


@router.websocket("/ws/meet/{mid}")
async def ws_meet(ws: WebSocket, mid: str):
    origin, host = ws.headers.get("origin"), ws.headers.get("host")
    if origin and origin.split("://", 1)[-1] != host:
        return await ws.close(code=4403)
    u = auth.user_from_token(ws.cookies.get(auth.COOKIE))
    try:
        m = _meeting_for(mid, u) if u else None
    except HTTPException:
        m = None
    if not m or _window_error(m):
        return await ws.close(code=4401)
    role = u["role"]
    await ws.accept()
    room = ROOMS.setdefault(mid, {})
    old = room.get(role)
    if old:  # same role reconnecting (refresh): replace the stale socket
        try:
            await old.close(code=4000)
        except Exception:
            pass
    room[role] = ws
    other = "candidate" if role == "hr" else "hr"
    log_event(mid, u["id"], "joined", role)
    await ws.send_json({"type": "peers", "present": [r for r in room if r != role]})
    if other in room:
        await room[other].send_json({"type": "peer_joined", "role": role})
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            t = msg.get("type")
            if t in RELAY and other in room:
                await room[other].send_json(msg)
            elif t == "chat":
                text = str(msg.get("text", "")).strip()[:1000]
                if text and other in room:
                    await room[other].send_json({
                        "type": "chat",
                        "text": text,
                        "sender": u["name"],
                        "role": role,
                        "at": now().isoformat(),
                    })
            elif t == "event" and role == "candidate":
                name = str(msg.get("name", ""))[:40]
                if name in {"consent_given", "screen_started", "screen_stopped", "screen_not_entire", "camera_stopped"}:
                    log_event(mid, u["id"], name, str(msg.get("detail", "")))
                    if "hr" in room:
                        await room["hr"].send_json({"type": "event", "name": name, "detail": msg.get("detail", ""),
                                                    "at": now().isoformat()})
    except (WebSocketDisconnect, ValueError):
        pass
    finally:
        if room.get(role) is ws:
            del room[role]
            log_event(mid, u["id"], "left", role)
            if other in room:
                try:
                    await room[other].send_json({"type": "peer_left", "role": role})
                except Exception:
                    pass
        if not room:
            ROOMS.pop(mid, None)


@router.get("/api/meetings/{mid}/events")
def events(mid: str, hr=Depends(auth.require_hr)):
    _meeting_for(mid, hr)
    with connect() as c:
        rows = c.execute("SELECT name, detail, created_utc FROM meeting_events WHERE meeting_id=? ORDER BY created_utc", (mid,)).fetchall()
    return [dict(r) for r in rows]
