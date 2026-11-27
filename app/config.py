import os
from pathlib import Path

BASE = Path(os.getenv("VERIFYOPS_HOME", Path(__file__).resolve().parent.parent))
DATA_DIR = Path(os.getenv("VERIFYOPS_DATA", BASE / "data"))
MODEL_DIR = Path(os.getenv("VERIFYOPS_MODEL_DIR", BASE / "models"))
MODEL_PATH = Path(os.getenv("VERIFYOPS_MODEL", MODEL_DIR / "corefakenet.onnx"))  # legacy single face model
DB_PATH = DATA_DIR / "verifyops.db"
HEATMAP_DIR = DATA_DIR / "heatmaps"
CERT_DIR = DATA_DIR / "certs"
KEY_PATH = DATA_DIR / "signing_key.pem"

API_KEYS = {k.strip() for k in os.getenv("VERIFYOPS_API_KEYS", "dev-key").split(",") if k.strip()}

# Verdict thresholds on trust_score (0-100, higher = more trustworthy)
PASS_AT = float(os.getenv("VERIFYOPS_PASS_AT", 70))
BLOCK_BELOW = float(os.getenv("VERIFYOPS_BLOCK_BELOW", 30))

# Perceptual-hash Hamming distance (of 64 bits) at or below which images are "duplicates"
DUP_MAX_DISTANCE = int(os.getenv("VERIFYOPS_DUP_DISTANCE", 6))
# Max allowed gap between photo capture time and device activation ping
EXIF_MAX_SKEW_HOURS = float(os.getenv("VERIFYOPS_EXIF_SKEW_HOURS", 48))
GPS_MAX_KM = float(os.getenv("VERIFYOPS_GPS_MAX_KM", 1.0))

for d in (DATA_DIR, HEATMAP_DIR, CERT_DIR):
    d.mkdir(parents=True, exist_ok=True)
