"""Independent test: score a trained ONNX model on YOUR OWN labelled images from a different source.

    python scripts/eval_folder.py --task face --data D:\my_test_faces
    # folder layout:   <data>/real/*.jpg   <data>/fake/*.jpg      (fake = what the model should flag)

Use images the model never saw and that come from a different place than the training data (e.g. real APM photos
vs. your own edited/AI-made ones). Prints AUC, plus real/fake accuracy at the model's saved threshold, and the
worst mistakes so you can look at them. Reads models/<task>.onnx (or --model_dir).
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def auc(s, y):
    s, y = np.asarray(s), np.asarray(y)
    pos, neg = (y == 1).sum(), (y == 0).sum()
    if not pos or not neg:
        return float("nan")
    r = np.empty(len(s)); r[s.argsort()] = np.arange(1, len(s) + 1)
    return float((r[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=["face", "scene", "document"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--model_dir", default="models")
    ap.add_argument("--limit", type=int, default=500, help="max images per class")
    a = ap.parse_args()
    import os
    os.environ["VERIFYOPS_MODEL_DIR"] = str(Path(a.model_dir).resolve())
    os.environ.setdefault("VERIFYOPS_DATA", str(Path("data/_eval_tmp").resolve()))
    from app.gate import model
    if a.task not in model.detector.models:
        sys.exit(f"No {a.task}.onnx in {a.model_dir}. Export one first (scripts/export_onnx.py).")
    itype = {"face": "face", "scene": "photo", "document": "document"}[a.task]
    scores, labels, names = [], [], []
    for y, cls in ((0, "real"), (1, "fake")):
        files = [p for p in sorted((Path(a.data) / cls).rglob("*")) if p.suffix.lower() in EXT][: a.limit]
        if not files:
            sys.exit(f"No images in {Path(a.data) / cls}")
        for p in files:
            try:
                scores.append(model.detector.predict(p.read_bytes(), itype)[a.task]); labels.append(y); names.append(str(p))
            except Exception as e:
                print("skip", p.name, e)
    s, y = np.array(scores), np.array(labels)
    print(f"\n{a.task}: {int((y==0).sum())} real, {int((y==1).sum())} fake")
    print(f"AUC {auc(s, y):.3f}")
    print(f"at the model's own threshold (score 0.5): real correct {np.mean(s[y==0] < .5):.1%}, fake caught {np.mean(s[y==1] >= .5):.1%}")
    bad = np.argsort(-(np.where(y == 0, s, 1 - s)))[:5]
    print("5 worst mistakes (look at these images):")
    for i in bad:
        print(f"  {'real' if y[i]==0 else 'fake'} scored {s[i]:.2f}  {names[i]}")
    print("\nRule of thumb: AUC < 0.7 on a new source = not ready; 0.7-0.85 = usable only with human review; > 0.85 = promising.")


if __name__ == "__main__":
    main()
