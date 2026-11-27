"""ONNX inference + ELA forensic heatmap.

The CorefakeNet weights are not bundled. Put the exported model at models/corefakenet.onnx
(see scripts/export_onnx.py). Until then `available` is False and the Gate returns only the
deterministic FieldProof/ELA signals: it never invents a model score.
"""
import io
import logging

import numpy as np
from PIL import Image, ImageChops, ImageOps

from .. import config

log = logging.getLogger("verifyops.model")
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class Detector:
    """Loads every models/<task>.onnx (face, scene, document) with its models/<task>.json sidecar.

    A legacy single models/corefakenet.onnx is treated as the 'face' model.
    """
    TASKS = ("face", "scene", "document")

    def __init__(self):
        self.models: dict[str, dict] = {}
        try:
            import onnxruntime as ort
        except Exception:
            log.warning("onnxruntime missing; ML disabled")
            return
        d = config.MODEL_DIR
        for task in self.TASKS:
            path = d / f"{task}.onnx"
            if task == "face" and not path.exists() and config.MODEL_PATH.exists():
                path = config.MODEL_PATH
            if not path.exists():
                continue
            try:
                meta = {}
                mj = d / f"{task}.json"
                if mj.exists():
                    import json
                    meta = json.loads(mj.read_text())
                sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
                inp = sess.get_inputs()[0]
                size = meta.get("img_size") or (inp.shape[-1] if isinstance(inp.shape[-1], int) else 224)
                self.models[task] = {"sess": sess, "input": inp.name, "size": size, "threshold": meta.get("threshold", 0.5),
                                     "mean": np.array(meta.get("mean", MEAN), dtype=np.float32),
                                     "std": np.array(meta.get("std", STD), dtype=np.float32)}
                log.info("Loaded %s model from %s", task, path)
            except Exception:
                log.exception("Failed to load %s model", task)

    @property
    def available(self) -> bool:
        return bool(self.models)

    def loaded(self) -> list[str]:
        return sorted(self.models)

    def _run(self, m: dict, img: Image.Image) -> float:
        x = (np.asarray(img.resize((m["size"], m["size"]), Image.BICUBIC), dtype=np.float32) / 255.0 - m["mean"]) / m["std"]
        out = np.asarray(m["sess"].run(None, {m["input"]: x.transpose(2, 0, 1)[None].astype(np.float32)})[0]).reshape(-1)
        logit = float(out[0]) if out.size == 1 else float(out[1] - out[0])
        # shift so each model's own validation-optimal threshold maps to 0.5
        t = min(max(m["threshold"], 1e-4), 1 - 1e-4)
        return float(1 / (1 + np.exp(-(logit - np.log(t / (1 - t))))))

    def _has_face(self, img: Image.Image) -> bool:
        try:
            import cv2
            g = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2GRAY)
            f = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            return len(f.detectMultiScale(g, 1.2, 5, minSize=(60, 60))) > 0
        except Exception:
            return False

    def predict(self, data: bytes, image_type: str = "auto") -> dict[str, float]:
        """Returns {task: P(fake)} for the models that apply. image_type: auto|photo|face|document."""
        if not self.models:
            return {}
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        if image_type == "face":
            want = ["face"]
        elif image_type == "document":
            want = ["document"]
        elif image_type == "photo":
            want = ["scene"]
        else:  # auto: scene model on everything, face model only if a face is actually present
            want = ["scene"] + (["face"] if "face" in self.models and self._has_face(img) else [])
        return {t: self._run(self.models[t], img) for t in want if t in self.models}


def ela(data: bytes, quality: int = 90) -> tuple[float, Image.Image]:
    """Error-level analysis. Returns (score 0-1, heatmap). Regions that recompress very differently
    from the rest of the image hint at local edits. It is a *cue* for the reviewer, not proof."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    diff = np.asarray(ImageChops.difference(img, Image.open(io.BytesIO(buf.getvalue()))).convert("L"), dtype=np.float32)
    if diff.max() == 0:
        return 0.0, Image.fromarray(np.zeros_like(diff, dtype=np.uint8)).convert("RGB")
    norm = diff / diff.max()
    # heterogeneity: how much of the energy is concentrated in a few blocks
    h, w = norm.shape
    bs = 16
    blocks = norm[: h // bs * bs, : w // bs * bs].reshape(h // bs, bs, w // bs, bs).mean(axis=(1, 3))
    score = float(np.clip((blocks.std() / (blocks.mean() + 1e-6)) / 3.0, 0, 1))
    heat = np.zeros((h, w, 3), dtype=np.uint8)
    heat[..., 0] = (norm * 255).astype(np.uint8)
    heat[..., 1] = (np.sqrt(norm) * 90).astype(np.uint8)
    return score, Image.fromarray(heat).resize(img.size)


def overlay(data: bytes, heat: Image.Image, alpha: float = 0.5) -> Image.Image:
    base = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    return Image.blend(base, heat.resize(base.size), alpha)


detector = Detector()
