"""EXIF + GPS + timestamp cross-validator against an IoT device activation ping."""
import io
import math
from datetime import datetime, timezone

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

from .. import config

EDITORS = ("photoshop", "gimp", "snapseed", "lightroom", "canva", "picsart", "pixlr", "paint")


def _ratio(v) -> float:
    return float(v[0]) / float(v[1]) if isinstance(v, tuple) else float(v)


def _dms(vals, ref) -> float:
    d, m, s = (_ratio(x) for x in vals)
    deg = d + m / 60 + s / 3600
    return -deg if ref in ("S", "W") else deg


def read_exif(data: bytes) -> dict:
    img = Image.open(io.BytesIO(data))
    raw = img.getexif()
    tags = {TAGS.get(k, k): v for k, v in raw.items()}
    try:
        sub = raw.get_ifd(0x8769)
        tags.update({TAGS.get(k, k): v for k, v in sub.items()})
    except Exception:
        pass
    gps = {}
    try:
        gps = {GPSTAGS.get(k, k): v for k, v in raw.get_ifd(0x8825).items()}
    except Exception:
        pass
    out = {"format": img.format, "size": img.size, "make": tags.get("Make"), "model": tags.get("Model"),
           "software": tags.get("Software"), "datetime_original": tags.get("DateTimeOriginal") or tags.get("DateTime"),
           "lat": None, "lon": None}
    if "GPSLatitude" in gps and "GPSLongitude" in gps:
        try:
            out["lat"] = _dms(gps["GPSLatitude"], gps.get("GPSLatitudeRef", "N"))
            out["lon"] = _dms(gps["GPSLongitude"], gps.get("GPSLongitudeRef", "E"))
        except Exception:
            pass
    return out


def _haversine_km(a, b, c, d) -> float:
    r = 6371.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _parse_dt(s) -> datetime | None:
    if not s:
        return None
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(str(s).strip().replace("Z", "+0000") if "%z" in fmt else str(s).strip(), fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(str(s))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def validate(data: bytes, activation: dict | None) -> tuple[dict, list[dict]]:
    """activation = {"time": ISO str, "lat": float, "lon": float} from the IoT device ping (optional).

    Returns (exif_summary, flags). Each flag: {code, severity (low|medium|high), detail}.
    EXIF is trivially spoofable, so missing/mismatched EXIF raises review risk; it never proves authenticity.
    """
    flags: list[dict] = []
    try:
        info = read_exif(data)
    except Exception as e:
        return {}, [{"code": "IMAGE_UNREADABLE", "severity": "high", "detail": str(e)}]

    if not info["make"] and not info["model"] and not info["datetime_original"]:
        flags.append({"code": "EXIF_STRIPPED", "severity": "medium",
                      "detail": "No camera make/model or capture time. Typical of WhatsApp forwards, screenshots or gallery re-uploads."})
    if info["software"] and any(e in str(info["software"]).lower() for e in EDITORS):
        flags.append({"code": "EDITING_SOFTWARE", "severity": "high", "detail": f"Software tag: {info['software']}"})
    if info["lat"] is None and (info["make"] or info["model"]):
        flags.append({"code": "NO_GPS", "severity": "low", "detail": "Camera EXIF present but no GPS fix."})

    if activation:
        cap = _parse_dt(info["datetime_original"])
        act = _parse_dt(activation.get("time"))
        if cap and act:
            gap_h = abs((cap - act).total_seconds()) / 3600
            info["capture_vs_activation_hours"] = round(gap_h, 2)
            if gap_h > config.EXIF_MAX_SKEW_HOURS:
                flags.append({"code": "TIMESTAMP_MISMATCH", "severity": "high",
                              "detail": f"Photo taken {gap_h:.1f}h from device activation (limit {config.EXIF_MAX_SKEW_HOURS}h)."})
        if info["lat"] is not None and activation.get("lat") is not None:
            km = _haversine_km(info["lat"], info["lon"], float(activation["lat"]), float(activation["lon"]))
            info["gps_distance_km"] = round(km, 3)
            if km > config.GPS_MAX_KM:
                flags.append({"code": "GPS_MISMATCH", "severity": "high",
                              "detail": f"Photo GPS is {km:.1f} km from device activation location (limit {config.GPS_MAX_KM} km)."})
    return info, flags
