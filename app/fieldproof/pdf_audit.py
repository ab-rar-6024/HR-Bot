"""PDF sanitizer for resumes, Aadhaar/PAN scans and dealer invoices.

Deterministic checks only: hidden text (tiny font, white-on-white, off-page), Unicode Tag
characters (U+E0000-E007F) and zero-width characters, metadata/edit-trail anomalies,
font mixing and incremental-update (edited-after-signing) signs. Also returns sanitized text.
"""
import re

import fitz  # PyMuPDF

TAG_CHARS = re.compile("[\U000E0000-\U000E007F]")
ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")
INJECTION_HINTS = re.compile(
    r"(ignore (all |any )?(previous|prior) instructions|system prompt|you are (now )?an? (ai|assistant)|"
    r"rank this (candidate|resume)|score (this|me) (10|ten)|disregard)", re.I)
EDIT_TOOLS = ("photoshop", "illustrator", "canva", "ilovepdf", "smallpdf", "sejda", "pdfescape", "foxit phantom", "wps")

MIN_FONT_PT = 4.0
WHITE_DELTA = 15  # RGB distance from the page background below which text is "invisible"


def _rgb(c: int) -> tuple[int, int, int]:
    return (c >> 16) & 255, (c >> 8) & 255, c & 255


def audit(data: bytes) -> dict:
    flags: list[dict] = []
    hidden: list[str] = []
    visible: list[str] = []
    fonts: set[str] = set()
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        return {"flags": [{"code": "PDF_UNREADABLE", "severity": "high", "detail": str(e)}], "sanitized_text": "", "pages": 0}

    for pno, page in enumerate(doc, 1):
        rect = page.rect
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for sp in line["spans"]:
                    t = sp["text"]
                    if not t.strip():
                        continue
                    fonts.add(sp["font"])
                    r, g, b = _rgb(sp["color"])
                    near_white = min(r, g, b) >= 255 - WHITE_DELTA
                    bx = fitz.Rect(sp["bbox"])
                    off_page = not rect.intersects(bx) or bx.x1 < 0 or bx.y1 < 0
                    tiny = sp["size"] < MIN_FONT_PT
                    reason = "tiny_font" if tiny else "white_text" if near_white else "off_page" if off_page else None
                    if reason:
                        hidden.append(f"p{pno}:{reason}:{t[:120]}")
                    else:
                        visible.append(t)

    full = "\n".join(visible)
    if hidden:
        flags.append({"code": "HIDDEN_TEXT", "severity": "high",
                      "detail": f"{len(hidden)} hidden span(s) (tiny, white-on-white or off-page).", "samples": hidden[:5]})
    raw_all = "".join(p.get_text() for p in doc)
    if TAG_CHARS.search(raw_all):
        flags.append({"code": "UNICODE_TAG_CHARS", "severity": "high",
                      "detail": "Invisible Unicode Tag characters (E0000-E007F) present."})
    if len(ZERO_WIDTH.findall(raw_all)) > 5:
        flags.append({"code": "ZERO_WIDTH_CHARS", "severity": "medium", "detail": "Many zero-width characters."})
    if INJECTION_HINTS.search(raw_all):
        flags.append({"code": "PROMPT_INJECTION_PHRASE", "severity": "high",
                      "detail": "Text addressed to an AI screener found in document."})

    meta = doc.metadata or {}
    producer = f"{meta.get('producer', '')} {meta.get('creator', '')}".lower()
    if any(t in producer for t in EDIT_TOOLS):
        flags.append({"code": "EDITING_TOOL_METADATA", "severity": "medium",
                      "detail": f"Producer/creator: {meta.get('producer')} / {meta.get('creator')}"})
    if meta.get("modDate") and meta.get("creationDate") and meta["modDate"] != meta["creationDate"]:
        flags.append({"code": "MODIFIED_AFTER_CREATION", "severity": "low",
                      "detail": f"created {meta['creationDate']} / modified {meta['modDate']}"})
    if len(re.findall(rb"%%EOF", data)) > 1:
        flags.append({"code": "INCREMENTAL_UPDATE", "severity": "medium",
                      "detail": "Multiple %%EOF markers: file was edited and re-saved incrementally."})
    families = {re.sub(r"^[A-Z]{6}\+", "", f).split("-")[0] for f in fonts}
    if len(families) > 5:
        flags.append({"code": "FONT_MIXING", "severity": "low", "detail": f"{len(families)} font families on a short document."})

    sanitized = ZERO_WIDTH.sub("", TAG_CHARS.sub("", full))
    return {"flags": flags, "sanitized_text": sanitized, "pages": len(doc), "metadata": meta, "hidden_samples": hidden[:10]}
