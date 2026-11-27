import hashlib
import io
import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from . import config
from .db import connect, dumps, init_db
from .evidence import vault
from .fieldproof import exif_check, pdf_audit, phash
from .gate import model, verdict
from .meet.routes import router as meet_router
from .review.ui import PAGE

log = logging.getLogger("verifyops")
MAX_BYTES = 15 * 1024 * 1024
WEBHOOK_ALLOW = {h.strip() for h in os.getenv("VERIFYOPS_WEBHOOK_HOSTS", "").split(",") if h.strip()}

app = FastAPI(title="ProofyX VerifyOps", version="0.1.0")
app.include_router(meet_router)


_tunnel_proc = None


def _load_dotenv():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _start_tunnel():
    global _tunnel_proc
    if os.getenv("VERIFYOPS_NO_TUNNEL") or _tunnel_proc is not None:
        return
    cf = shutil.which("cloudflared") or r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
    if not Path(cf).is_file():
        return
    _tunnel_proc = subprocess.Popen(
        [cf, "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    def _watch():
        found = False
        for line in _tunnel_proc.stdout:
            if not found:
                m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
                if m:
                    found = True
                    url = m.group(0)
                    os.environ["VERIFYOPS_PUBLIC_URL"] = url
                    print(f"\n[ProofyX] Public HTTPS URL: {url}\n", flush=True)

    threading.Thread(target=_watch, daemon=True).start()


@app.on_event("startup")
def _startup():
    if "pytest" not in sys.modules:
        _load_dotenv()
        _start_tunnel()
    init_db()
    vault.public_key_pem()  # create signing key on first boot


@app.on_event("shutdown")
def _shutdown():
    global _tunnel_proc
    if _tunnel_proc is not None:
        _tunnel_proc.terminate()
        _tunnel_proc = None


def auth(x_api_key: str = Header(default="")):
    if not any(secrets.compare_digest(x_api_key, k) for k in config.API_KEYS):
        raise HTTPException(401, "Invalid or missing X-API-Key")


def _sniff(data: bytes) -> str:
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n" or data[:4] == b"RIFF" or data[:2] == b"BM":
        return "image"
    raise HTTPException(415, "Unsupported file type (JPEG, PNG, WEBP, BMP, PDF only)")


def _fire_webhook(url: str, body: dict):
    try:
        httpx.post(url, json=body, timeout=10)
    except Exception as e:
        log.warning("webhook to %s failed: %s", url, e)


@app.get("/health")
def health():
    return {"status": "ok", "ml_model_loaded": model.detector.available, "models": model.detector.loaded()}


@app.post("/api/v1/verify", dependencies=[Depends(auth)])
def verify(
    bg: BackgroundTasks,
    file: UploadFile = File(...),
    entity_id: str | None = Form(None, description="Vehicle / invoice / employee id this file supports"),
    dealer_id: str | None = Form(None),
    activation_time: str | None = Form(None, description="ISO-8601 time of IoT device activation ping"),
    activation_lat: float | None = Form(None),
    activation_lon: float | None = Form(None),
    webhook_url: str | None = Form(None),
    issue_certificate: bool = Form(True),
    image_type: str = Form("auto", description="auto | photo | face | document"),
):
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File exceeds 15 MB")
    if not data:
        raise HTTPException(400, "Empty file")
    kind = _sniff(data)
    vid = str(uuid.uuid4())
    sha = hashlib.sha256(data).hexdigest()
    flags: list[dict] = []
    analysis: dict = {"kind": kind}
    heat_path = None
    fake_prob = ela_score = None

    # Exact-bytes replay is the cheapest duplicate check and works for PDFs too.
    with connect() as c:
        same = c.execute("SELECT id, created_utc FROM verifications WHERE sha256=? LIMIT 1", (sha,)).fetchone()
    if same:
        flags.append({"code": "DUPLICATE_FILE", "severity": "high",
                      "detail": f"Byte-identical file already verified ({same['id']} at {same['created_utc']})."})

    if kind == "image":
        try:
            ph, dh = phash.hashes(data)
        except Exception as e:
            raise HTTPException(422, f"Cannot decode image: {e}")
        dups = phash.find_duplicates(ph, dh, exclude_id=vid)
        if dups:
            analysis["duplicate_matches"] = dups
            flags.append({"code": "DUPLICATE_IMAGE", "severity": "high",
                          "detail": f"Visually matches {len(dups)} earlier submission(s); closest was for entity "
                                    f"{dups[0]['entity_id']} (pHash distance {dups[0]['phash_distance']})."})
        activation = None
        if activation_time or activation_lat is not None:
            activation = {"time": activation_time, "lat": activation_lat, "lon": activation_lon}
        exif, ex_flags = exif_check.validate(data, activation)
        flags += ex_flags
        analysis["exif"] = exif
        scores = model.detector.predict(data, image_type if image_type in ("auto", "photo", "face", "document") else "auto")
        fake_prob = max(scores.values()) if scores else None  # any model raising the alarm counts
        ela_score, heat = model.ela(data)
        heat_path = config.HEATMAP_DIR / f"{vid}.jpg"
        model.overlay(data, heat).save(heat_path, quality=88)
        analysis.update(model_fake_probability=fake_prob, model_scores=scores, ela_score=round(ela_score, 3),
                        ml_model_loaded=model.detector.available, models_loaded=model.detector.loaded())
        phash.register(vid, ph, dh, entity_id, dealer_id)
    else:
        rep = pdf_audit.audit(data)
        flags += rep["flags"]
        analysis.update(pages=rep["pages"], metadata=rep.get("metadata"), hidden_samples=rep.get("hidden_samples"),
                        model_fake_probability=None, ela_score=None, ml_model_loaded=False)

    v = verdict.fuse(fake_prob, ela_score, flags)
    result = {
        "id": vid, "filename": file.filename, "sha256": sha, **v,
        "forensic_flags": flags, "analysis": analysis,
        "context": {"entity_id": entity_id, "dealer_id": dealer_id},
        "gradcam_heatmap_url": f"/api/v1/verifications/{vid}/heatmap" if heat_path else None,
        "heatmap_kind": "ela_overlay" if heat_path else None,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    status = "pending" if v["recommended_action"] in ("REVIEW", "BLOCK") else "none"
    with connect() as c:
        c.execute("INSERT INTO verifications VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (vid, result["created_utc"], file.filename, kind, sha, dumps(result["context"]), v["trust_score"],
                   v["confidence_band"], v["recommended_action"], dumps(flags), dumps(result),
                   str(heat_path) if heat_path else None, status, None))
    if issue_certificate:
        cert = vault.issue(result, str(heat_path) if heat_path else None)
        result["certificate_url"] = f"/api/v1/verifications/{vid}/certificate"
        result["certificate_sha256"] = cert["certificate_sha256"]
    if webhook_url:
        host = urlparse(webhook_url).hostname or ""
        if host in WEBHOOK_ALLOW:  # allow-list prevents the API being used as an SSRF proxy
            bg.add_task(_fire_webhook, webhook_url, result)
        else:
            result["webhook_skipped"] = "host not in VERIFYOPS_WEBHOOK_HOSTS"
    return result


def _get(vid: str):
    with connect() as c:
        r = c.execute("SELECT * FROM verifications WHERE id=?", (vid,)).fetchone()
    if not r:
        raise HTTPException(404, "Not found")
    return r


@app.get("/api/v1/verifications/{vid}", dependencies=[Depends(auth)])
def get_verification(vid: str):
    import json
    return json.loads(_get(vid)["result"])


@app.get("/api/v1/verifications/{vid}/heatmap", dependencies=[Depends(auth)])
def heatmap(vid: str):
    r = _get(vid)
    if not r["heatmap_path"]:
        raise HTTPException(404, "No heatmap for this file type")
    return FileResponse(r["heatmap_path"], media_type="image/jpeg")


@app.get("/api/v1/verifications/{vid}/certificate", dependencies=[Depends(auth)])
def certificate(vid: str, format: str = "pdf"):
    _get(vid)
    p = config.CERT_DIR / f"{vid}.{'json' if format == 'json' else 'pdf'}"
    if not p.exists():
        raise HTTPException(404, "No certificate issued")
    return FileResponse(p, media_type="application/json" if format == "json" else "application/pdf")


@app.get("/api/v1/evidence/public-key")
def public_key():
    return JSONResponse({"algorithm": "Ed25519", "public_key_pem": vault.public_key_pem()})


@app.get("/api/v1/evidence/verify-chain", dependencies=[Depends(auth)])
def verify_chain():
    """Re-check every stored certificate: signature valid and hash chain unbroken."""
    import json
    with connect() as c:
        rows = c.execute("SELECT * FROM certificates ORDER BY created_utc, rowid").fetchall()
    prev, problems = None, []
    for r in rows:
        jp = config.CERT_DIR / f"{r['verification_id']}.json"
        try:
            doc = json.loads(jp.read_text())
        except Exception:
            problems.append({"id": r["verification_id"], "problem": "certificate file missing/corrupt"})
            prev = r["cert_sha256"]
            continue
        body = {"payload": doc["payload"], "signature_ed25519": doc["signature_ed25519"]}
        if hashlib.sha256(vault.canonical(body)).hexdigest() != r["cert_sha256"]:
            problems.append({"id": r["verification_id"], "problem": "content hash mismatch (file altered)"})
        if not vault.verify_signature(doc["payload"], doc["signature_ed25519"]):
            problems.append({"id": r["verification_id"], "problem": "bad signature"})
        if r["prev_cert_sha256"] != prev:
            problems.append({"id": r["verification_id"], "problem": "chain link broken"})
        prev = r["cert_sha256"]
    return {"certificates_checked": len(rows), "intact": not problems, "problems": problems}


# ---------- Review queue ----------
@app.get("/review", response_class=HTMLResponse)
def review_page():
    return PAGE


@app.get("/api/v1/review/queue", dependencies=[Depends(auth)])
def queue(limit: int = 50):
    import json
    with connect() as c:
        rows = c.execute("SELECT result FROM verifications WHERE review_status='pending' "
                         "ORDER BY CASE action WHEN 'BLOCK' THEN 0 ELSE 1 END, created_utc LIMIT ?", (limit,)).fetchall()
    return [json.loads(r["result"]) for r in rows]


@app.post("/api/v1/review/{vid}", dependencies=[Depends(auth)])
def label(vid: str, decision: str = Form(...), reviewer: str = Form("unknown")):
    if decision not in ("fraud", "authentic"):
        raise HTTPException(422, "decision must be 'fraud' or 'authentic'")
    _get(vid)
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute("UPDATE verifications SET review_status=?, reviewed_utc=? WHERE id=?", (decision, now, vid))
        c.execute("INSERT INTO labels VALUES (?,?,?,?)", (vid, decision, reviewer, now))
    return {"id": vid, "review_status": decision}


@app.get("/api/v1/review/export-labels", dependencies=[Depends(auth)])
def export_labels():
    """Labeled data for the active-learning loop (Phase 4): file hash + label + model score."""
    import json
    with connect() as c:
        rows = c.execute("SELECT v.id, v.sha256, v.kind, v.result, l.label, l.created_utc FROM labels l "
                         "JOIN verifications v ON v.id=l.verification_id").fetchall()
    return [{"id": r["id"], "sha256": r["sha256"], "kind": r["kind"], "label": r["label"],
             "model_fake_probability": json.loads(r["result"])["analysis"].get("model_fake_probability"),
             "labeled_utc": r["created_utc"]} for r in rows]


@app.get("/api/v1/stats", dependencies=[Depends(auth)])
def stats():
    with connect() as c:
        rows = c.execute("SELECT action, COUNT(*) n FROM verifications GROUP BY action").fetchall()
    total = sum(r["n"] for r in rows) or 1
    return {"total": sum(r["n"] for r in rows),
            "by_action": {r["action"]: r["n"] for r in rows},
            "escalation_rate_pct": round(100 * sum(r["n"] for r in rows if r["action"] != "PASS") / total, 2)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
