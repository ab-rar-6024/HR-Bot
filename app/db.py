import json
import sqlite3
import threading
from contextlib import contextmanager

from .config import DB_PATH

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS verifications (
    id TEXT PRIMARY KEY,
    created_utc TEXT NOT NULL,
    filename TEXT,
    kind TEXT NOT NULL,              -- image | pdf
    sha256 TEXT NOT NULL,
    context TEXT,                    -- json: dealer_id, vehicle_id, ...
    trust_score REAL,
    confidence_band TEXT,
    action TEXT NOT NULL,            -- PASS | REVIEW | BLOCK
    flags TEXT NOT NULL,             -- json list
    result TEXT NOT NULL,            -- full json verdict
    heatmap_path TEXT,
    review_status TEXT DEFAULT 'none',   -- none | pending | fraud | authentic
    reviewed_utc TEXT
);
CREATE INDEX IF NOT EXISTS ix_ver_action ON verifications(action, review_status);
CREATE INDEX IF NOT EXISTS ix_ver_sha ON verifications(sha256);

CREATE TABLE IF NOT EXISTS image_hashes (
    verification_id TEXT NOT NULL,
    phash INTEGER NOT NULL,          -- 64-bit stored as signed int
    dhash INTEGER NOT NULL,
    entity_id TEXT,                  -- vehicle / invoice id the photo was submitted for
    dealer_id TEXT,
    created_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS certificates (
    verification_id TEXT PRIMARY KEY,
    pdf_path TEXT NOT NULL,
    cert_sha256 TEXT NOT NULL,
    prev_cert_sha256 TEXT,           -- hash chain links certificates together
    created_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,              -- hr | candidate
    pw_hash TEXT NOT NULL,
    must_change INTEGER DEFAULT 0,
    created_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meetings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    hr_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    start_utc TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    created_utc TEXT NOT NULL,
    cancelled INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS meeting_events (
    meeting_id TEXT NOT NULL,
    user_id TEXT,
    name TEXT NOT NULL,              -- consent_given | joined | left | screen_started | screen_stopped ...
    detail TEXT,
    created_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS labels (
    verification_id TEXT NOT NULL,
    label TEXT NOT NULL,             -- fraud | authentic
    reviewer TEXT,
    created_utc TEXT NOT NULL
);
"""


def init_db():
    with connect() as c:
        c.executescript(SCHEMA)


@contextmanager
def connect():
    with _lock:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def dumps(o) -> str:
    return json.dumps(o, default=str)
