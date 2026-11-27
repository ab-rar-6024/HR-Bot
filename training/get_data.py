"""Download and arrange public datasets as  OUT/{train,val}/{real,fake}/*.jpg  (fake = 1).

    python training/get_data.py scene --out /content/data_scene --per_class 6000
    python training/get_data.py face  --out /content/data_face  --per_class 6000
    python training/get_data.py docs  --out /content/real_docs  --per_class 3000   # then make_doc_fakes.py

Every image is re-saved as JPEG at a random quality for BOTH classes. Many public sets store real photos as JPEG
and fakes as PNG; without this the model just learns the file format and fails on real uploads.

LICENCES: TheKernel01/Tiny-GenImage is CC-BY-NC-SA (non-commercial). pujanpaudel/deepfake_face_classification is
Apache-2.0 but derives from DF40 (research terms). Models trained on them may not be usable in a paid product:
check with counsel, and prefer fine-tuning on your own consented APM data before commercial release.
"""
import argparse
import io
import random
import sys
from pathlib import Path

from PIL import Image

random.seed(0)
EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def save(img: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "JPEG", quality=random.randint(70, 95))


def scene(a):
    """Generator-balanced sample of Tiny-GenImage. The stream is stored sorted, so a plain shuffled sample can contain only
    one or two generators; we instead take an equal quota from every fake generator (and from reals) in BOTH splits."""
    import math
    from collections import Counter
    from datasets import load_dataset
    for split, out_split, cap in (("train", "train", a.per_class), ("validation", "val", max(a.per_class // 5, 200))):
        ds = load_dataset("TheKernel01/Tiny-GenImage", split=split, streaming=True)
        labels, gens = ds.features["label"].names, ds.features["generator"].names  # label: real/fake; generator: Real, ADM, ...
        fake_gens = [g for g in gens if g.lower() != "real"]
        quota = {"Real": cap, **{g: math.ceil(cap / len(fake_gens)) for g in fake_gens}}
        got, idx = Counter(), Counter()
        for ex in ds.shuffle(seed=0, buffer_size=5000):
            g = gens[ex["generator"]]
            y = ex["label"] if isinstance(ex["label"], int) else labels.index(ex["label"])
            if y == 0:
                g = "Real"
            if got[g] >= quota.get(g, 0):
                if all(got[k] >= q for k, q in quota.items()):
                    break
                continue
            cls = "fake" if y else "real"
            save(ex["image"], Path(a.out) / out_split / cls / f"{idx[cls]:06d}.jpg")
            idx[cls] += 1
            got[g] += 1
        print(split, "saved per source:", dict(got))
        short = [k for k, q in quota.items() if got[k] < q]
        if short:
            print(f"  WARNING: fewer images than wanted for {short}")


def _extract(archive: Path, dest: Path) -> bool:
    """Extract .zip natively; .rar via unrar/unar/7z (installing `unar` on Colab if needed). Returns success."""
    import shutil
    import subprocess
    import zipfile
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)
        return True
    tools = [["unrar", "x", "-o+", "-idq", str(archive), str(dest) + "/"], ["unar", "-q", "-o", str(dest), str(archive)],
             ["7z", "x", "-y", f"-o{dest}", str(archive)]]
    for attempt in range(2):
        for cmd in tools:
            if shutil.which(cmd[0]):
                if subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                    return True
        if attempt == 0 and shutil.which("apt-get"):  # Colab: install an extractor, then retry once
            subprocess.run("apt-get -qq install -y unar >/dev/null 2>&1 || (apt-get -qq update >/dev/null 2>&1 && apt-get -qq install -y unar >/dev/null 2>&1)", shell=True)
    return False


def _label(rel_parts):
    txt = "/".join(p.lower() for p in rel_parts)
    if any(t in txt for t in ("fake", "synthetic", "generated", "deepfake")):
        return 1
    return 0 if "real" in txt else None


def _collect(root: Path):
    out = {0: [], 1: []}
    for p in root.rglob("*"):
        if p.suffix.lower() in EXT:
            y = _label(p.relative_to(root).parts)
            if y is not None:
                out[y].append(p)
    return out


def faces(a):
    """DF40-derived face set. The repo ships val.zip, test.zip and train.rar (not loose images)."""
    from huggingface_hub import hf_hub_download
    raw = Path(a.out).parent / (Path(a.out).name + "_raw")
    got = {}
    plan = [("val", "val.zip"), ("test", "test.zip")] + ([] if getattr(a, "quick", False) else [("train", "train.rar")])
    for split, fname in plan:  # quick test skips the 3.9 GB train.rar
        print(f"downloading {fname} ...", flush=True)
        arc = Path(hf_hub_download(a.repo, fname, repo_type="dataset"))
        ok = _extract(arc, raw / split)
        if not ok:
            print(f"WARNING: could not extract {fname}; continuing without it")
            continue
        got[split] = _collect(raw / split)
        print(split, {("fake" if y else "real"): len(v) for y, v in got[split].items()}, flush=True)
    if "train" in got and all(got["train"].values()):
        parts = {"train": got["train"], "val": got["val"]}  # test split stays untouched as an unseen hold-out
    else:
        print("train.rar unavailable: training on the test.zip images and validating on val.zip (smaller, but works)")
        parts = {"train": got["test"], "val": got["val"]}
    for split, lab in parts.items():
        cap = a.per_class if split == "train" else max(a.per_class // 5, 200)
        for y, lst in lab.items():
            random.shuffle(lst)
            for i, p in enumerate(lst[:cap]):
                try:
                    save(Image.open(p), Path(a.out) / split / ("fake" if y else "real") / f"{i:06d}.jpg")
                except Exception:
                    pass
            print(split, "fake" if y else "real", min(len(lst), cap))
    if not any((Path(a.out) / "train" / c).exists() for c in ("real", "fake")):
        sys.exit("No face images were prepared; check the archive layout under " + str(raw))
    print("NOTE: DF40 licence is CC BY-NC 4.0 (non-commercial). Test the model on images from a different source.")


DOC_REPOS = ["Francisco-Cruz/InvoicesReceiptsPT", "Voxel51/scanned_receipts", "Divya52/indian-gst-invoices"]


def docs(a):
    """Collect REAL document images (no labels) for training/make_doc_fakes.py. Add your own scans/invoices too."""
    from huggingface_hub import snapshot_download
    n = 0
    for repo in DOC_REPOS:
        if n >= a.per_class:   # enough already: don't download the remaining datasets (saves ~10 min in quick tests)
            break
        try:
            root = Path(snapshot_download(repo, repo_type="dataset", allow_patterns=["*.jpg", "*.jpeg", "*.png"]))
        except Exception as e:
            print("skip", repo, e)
            continue
        for p in root.rglob("*"):
            if p.suffix.lower() in EXT and n < a.per_class:
                try:
                    save(Image.open(p), Path(a.out) / f"{n:06d}.jpg")
                    n += 1
                except Exception:
                    pass
    print(f"collected {n} document images into {a.out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["scene", "face", "docs"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--per_class", type=int, default=6000)
    ap.add_argument("--repo", default="pujanpaudel/deepfake_face_classification")
    a = ap.parse_args()
    {"scene": scene, "face": faces, "docs": docs}[a.which](a)
