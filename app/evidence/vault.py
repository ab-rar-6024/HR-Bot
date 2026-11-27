"""EvidenceVault: tamper-evident Verification Certificates.

Each certificate records the SHA-256 of the original file, a UTC timestamp, the verdict and the
forensic breakdown. Certificates are hash-chained (each embeds the previous certificate's hash)
and the certificate payload is signed with an Ed25519 key kept on the customer's premises.

NOTE: this produces a documented chain of custody. Admissibility under BSA s.63 requires the
s.63(4) certificate to be signed by the person in charge of the device and an expert; have counsel
review the wording before presenting this to a court or marketing it as "compliant".
"""
import hashlib
import io
import json
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .. import config
from ..db import connect


def _key() -> Ed25519PrivateKey:
    if config.KEY_PATH.exists():
        return serialization.load_pem_private_key(config.KEY_PATH.read_bytes(), password=None)
    k = Ed25519PrivateKey.generate()
    config.KEY_PATH.write_bytes(k.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return k


def public_key_pem() -> str:
    return _key().public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def sign(payload: dict) -> str:
    return _key().sign(canonical(payload)).hex()


def verify_signature(payload: dict, signature_hex: str) -> bool:
    try:
        _key().public_key().verify(bytes.fromhex(signature_hex), canonical(payload))
        return True
    except Exception:
        return False


def _last_cert_hash() -> str | None:
    with connect() as c:
        r = c.execute("SELECT cert_sha256 FROM certificates ORDER BY created_utc DESC, rowid DESC LIMIT 1").fetchone()
    return r["cert_sha256"] if r else None


def issue(verification: dict, heatmap_path: str | None = None, branding: str = "ProofyX Verified Evidence") -> dict:
    vid = verification["id"]
    prev = _last_cert_hash()
    payload = {
        "certificate_version": 1,
        "verification_id": vid,
        "issued_utc": datetime.now(timezone.utc).isoformat(),
        "file_sha256": verification["sha256"],
        "filename": verification.get("filename"),
        "verdict": {k: verification[k] for k in ("trust_score", "confidence_band", "recommended_action")},
        "forensic_flags": verification["forensic_flags"],
        "analysis": verification.get("analysis", {}),
        "context": verification.get("context", {}),
        "prev_certificate_sha256": prev,
    }
    sig = sign(payload)
    body = {"payload": payload, "signature_ed25519": sig}
    cert_hash = hashlib.sha256(canonical(body)).hexdigest()

    path = config.CERT_DIR / f"{vid}.pdf"
    _render_pdf(path, branding, payload, sig, cert_hash, heatmap_path)
    # Machine-readable twin so a third party can re-verify without the PDF
    (config.CERT_DIR / f"{vid}.json").write_text(json.dumps({**body, "certificate_sha256": cert_hash}, indent=2, default=str))

    with connect() as c:
        c.execute("INSERT OR REPLACE INTO certificates VALUES (?,?,?,?,?)",
                  (vid, str(path), cert_hash, prev, payload["issued_utc"]))
    return {"certificate_sha256": cert_hash, "pdf_path": str(path), "prev_certificate_sha256": prev}


def _render_pdf(path, branding, p, sig, cert_hash, heatmap_path):
    ss = getSampleStyleSheet()
    mono = ss["Code"]
    mono.fontSize = 7
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    v = p["verdict"]
    colour = {"PASS": colors.HexColor("#1a7f37"), "REVIEW": colors.HexColor("#b26a00"), "BLOCK": colors.HexColor("#b42318")}[v["recommended_action"]]
    el = [Paragraph(branding, ss["Title"]), Paragraph("Verification Certificate / Chain-of-Custody Record", ss["Heading3"]), Spacer(1, 4 * mm)]
    rows = [["Verification ID", p["verification_id"]], ["Issued (UTC)", p["issued_utc"]], ["File name", str(p.get("filename"))],
            ["File SHA-256", p["file_sha256"]], ["Trust score", f'{v["trust_score"]} / 100'],
            ["Confidence", v["confidence_band"]], ["Recommended action", v["recommended_action"]]]
    t = Table([[a, Paragraph(str(b), mono if "SHA" in a else ss["Normal"])] for a, b in rows], colWidths=[40 * mm, 130 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                           ("TEXTCOLOR", (1, 6), (1, 6), colour), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    el += [t, Spacer(1, 5 * mm), Paragraph("Forensic findings", ss["Heading3"])]
    flags = p["forensic_flags"]
    if flags:
        ft = Table([["Code", "Severity", "Detail"]] + [[f["code"], f["severity"], Paragraph(str(f["detail"]), ss["Normal"])] for f in flags],
                   colWidths=[42 * mm, 20 * mm, 108 * mm])
        ft.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke)]))
        el.append(ft)
    else:
        el.append(Paragraph("No forensic flags raised.", ss["Normal"]))
    a = p.get("analysis", {})
    el += [Spacer(1, 4 * mm), Paragraph("Model breakdown", ss["Heading3"]),
           Paragraph(f'ML model: {"loaded, P(fake)=%.3f" % a["model_fake_probability"] if a.get("model_fake_probability") is not None else "NOT AVAILABLE for this run (deterministic checks only)"}'
                     f'<br/>ELA inconsistency score: {a.get("ela_score")}', ss["Normal"])]
    if heatmap_path:
        try:
            el += [Spacer(1, 3 * mm), RLImage(heatmap_path, width=90 * mm, height=65 * mm, kind="proportional")]
        except Exception:
            pass
    el += [Spacer(1, 6 * mm), Paragraph("Integrity", ss["Heading3"]),
           Paragraph(f"Previous certificate SHA-256: {p['prev_certificate_sha256'] or 'GENESIS'}", mono),
           Paragraph(f"Certificate SHA-256: {cert_hash}", mono),
           Paragraph(f"Ed25519 signature: {sig}", mono), Spacer(1, 3 * mm),
           Paragraph("This record is machine-generated analysis to support, not replace, human review. "
                     "Signature can be verified with the issuer's public key via GET /api/v1/evidence/public-key.", ss["Italic"])]
    doc.build(el)
