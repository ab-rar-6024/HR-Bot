"""Fuse model + FieldProof signals into trust_score / PASS-REVIEW-BLOCK."""
from .. import config

SEV_PENALTY = {"low": 5, "medium": 15, "high": 40}


def fuse(fake_prob: float | None, ela_score: float | None, flags: list[dict]) -> dict:
    score = 100.0
    if fake_prob is not None:
        score -= 70 * fake_prob
    if ela_score is not None and ela_score > 0.6:
        score -= 10 * (ela_score - 0.6) / 0.4
    for f in flags:
        score -= SEV_PENALTY.get(f["severity"], 5)
    score = max(0.0, min(100.0, score))

    hard_block = any(f["code"] in ("DUPLICATE_IMAGE", "HIDDEN_TEXT", "UNICODE_TAG_CHARS", "PROMPT_INJECTION_PHRASE")
                     for f in flags)
    if hard_block or score < config.BLOCK_BELOW:
        action = "BLOCK"
    elif score >= config.PASS_AT and not any(f["severity"] == "high" for f in flags):
        action = "PASS"
    else:
        action = "REVIEW"

    # Confidence is lower when the ML model is absent or the score sits near a threshold.
    margin = min(abs(score - config.PASS_AT), abs(score - config.BLOCK_BELOW))
    if fake_prob is None:
        band = "LOW" if margin < 25 else "MEDIUM"
    else:
        band = "HIGH" if margin >= 20 else "MEDIUM" if margin >= 8 else "LOW"
    return {"trust_score": round(score, 1), "confidence_band": band, "recommended_action": action}
