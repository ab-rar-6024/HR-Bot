"""Perceptual-hash duplicate vault (pure numpy + Pillow, no extra dependency)."""
import io
from datetime import datetime, timezone

import numpy as np
from PIL import Image, ImageOps

from .. import config
from ..db import connect


def _gray(img: Image.Image, size) -> np.ndarray:
    return np.asarray(ImageOps.exif_transpose(img).convert("L").resize(size, Image.LANCZOS), dtype=np.float64)


def _to_signed(v: int) -> int:
    return v - (1 << 64) if v >= (1 << 63) else v


def _to_unsigned(v: int) -> int:
    return v + (1 << 64) if v < 0 else v


def dhash(img: Image.Image) -> int:
    px = _gray(img, (9, 8))
    bits = (px[:, 1:] > px[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def phash(img: Image.Image) -> int:
    n = 32
    px = _gray(img, (n, n))
    k = np.arange(n)
    dct = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))  # DCT-II basis
    low = (dct @ px @ dct.T)[:8, :8]
    med = np.median(low.flatten()[1:])
    bits = (low > med).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def hashes(data: bytes) -> tuple[int, int]:
    img = Image.open(io.BytesIO(data))
    return phash(img), dhash(img)


def find_duplicates(ph: int, dh: int, exclude_id: str | None = None, limit: int = 5) -> list[dict]:
    """Linear scan; fine up to ~1M rows on SQLite. Swap for a BK-tree/pgvector later."""
    out = []
    with connect() as c:
        rows = c.execute("SELECT verification_id, phash, dhash, entity_id, dealer_id, created_utc FROM image_hashes").fetchall()
    for r in rows:
        if r["verification_id"] == exclude_id:
            continue
        dp = hamming(ph, _to_unsigned(r["phash"]))
        dd = hamming(dh, _to_unsigned(r["dhash"]))
        # Require both hashes to be close; a crop/resize/WhatsApp recompress keeps both low.
        if dp <= config.DUP_MAX_DISTANCE and dd <= config.DUP_MAX_DISTANCE + 4:
            out.append({
                "matched_verification_id": r["verification_id"],
                "phash_distance": dp, "dhash_distance": dd,
                "entity_id": r["entity_id"], "dealer_id": r["dealer_id"],
                "first_seen_utc": r["created_utc"],
            })
    out.sort(key=lambda m: m["phash_distance"] + m["dhash_distance"])
    return out[:limit]


def register(verification_id: str, ph: int, dh: int, entity_id: str | None, dealer_id: str | None):
    with connect() as c:
        c.execute(
            "INSERT INTO image_hashes VALUES (?,?,?,?,?,?)",
            (verification_id, _to_signed(ph), _to_signed(dh), entity_id, dealer_id,
             datetime.now(timezone.utc).isoformat()),
        )
