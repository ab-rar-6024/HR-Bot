"""ProofyX model #1: FACE deepfake detector (EfficientNet-B4).   (Runtime > Change runtime type > GPU)
Data: DF40-derived faces from Hugging Face (val.zip + test.zip + the 3.9 GB train.rar).

HOW TO RUN (script mode, recommended)
  1. Upload this file to Colab (folder icon > upload icon). It lands at /content/train_face.py
  2. Cell A (Drive, do once per session):
         from google.colab import drive
         drive.mount('/content/drive')
  3. Cell B (few-minute test, saves face_quick.pth):
         !python -u /content/train_face.py --quick
  4. Cell C (the real run, several hours on a T4, saves face.pth):
         !python -u /content/train_face.py --full
If Colab disconnects, run Cell A then Cell C again: it resumes from the last finished epoch.
Outputs: MyDrive/proofyx/face.pth  (also downloaded to your computer when finished).
"""
TASK = "face"
QUICK_TEST = True        # default is the safe quick test; pass --full for the real run
PER_CLASS = 6000         # images per class for the real run
# ------------------------------------------------------------------------------------------------------------
import subprocess, sys
def _pip(*pk):
    subprocess.check_call([sys.executable, "-m", "pip", "-q", "install", *pk])
for _mod, _pkg in (("datasets", "datasets"), ("transformers", "transformers"), ("huggingface_hub", "huggingface_hub")):
    try:
        __import__(_mod)
    except ImportError:
        _pip(_pkg)

# ===== model definitions =====
import torch
import torch.nn as nn
from torchvision import models

IMAGENET = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
CLIP_NORM = ([0.48145466, 0.4578275, 0.40821073], [0.26862954, 0.26130258, 0.27577711])

TASKS = {
    # task: (default arch, image size, description)
    "face":     ("efficientnet_b4", 380, "face deepfakes / face swaps (face crops)"),
    "scene":    ("clip_vit_b16",    224, "AI-generated or edited photos: installation shots, vehicles, scenes"),
    "document": ("convnext_tiny",   384, "tampered ID cards / invoices / scanned documents"),
}


def norm_for(arch: str):
    return CLIP_NORM if arch.startswith("clip") else IMAGENET


class ClipDetector(nn.Module):
    """CLIP vision tower + linear head. `backbone` params are the CLIP tower; `head` is the classifier."""

    def __init__(self, pretrained=True, name="openai/clip-vit-base-patch16"):
        super().__init__()
        from transformers import CLIPVisionConfig, CLIPVisionModel
        self.backbone = CLIPVisionModel.from_pretrained(name) if pretrained else CLIPVisionModel(
            CLIPVisionConfig(hidden_size=768, intermediate_size=3072, num_hidden_layers=12, num_attention_heads=12,
                             image_size=224, patch_size=16, projection_dim=512))  # real ViT-B/16 shape, random weights
        self.head = nn.Linear(self.backbone.config.hidden_size, 1)

    def forward(self, x):
        return self.head(self.backbone(pixel_values=x).pooler_output)


def build(arch: str, pretrained: bool = True) -> nn.Module:
    if arch == "efficientnet_b4":
        m = models.efficientnet_b4(weights="IMAGENET1K_V1" if pretrained else None)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, 1)
    elif arch == "efficientnet_b0":
        m = models.efficientnet_b0(weights="IMAGENET1K_V1" if pretrained else None)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, 1)
    elif arch == "convnext_tiny":
        m = models.convnext_tiny(weights="IMAGENET1K_V1" if pretrained else None)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, 1)
    elif arch == "resnet50":
        m = models.resnet50(weights="IMAGENET1K_V2" if pretrained else None)
        m.fc = nn.Linear(m.fc.in_features, 1)
    elif arch == "clip_vit_b16":
        m = ClipDetector(pretrained)
    else:
        raise ValueError(f"unknown arch {arch}")
    return m


def head_params(model: nn.Module):
    """The freshly initialised classifier layer (trained first while the backbone is frozen)."""
    if isinstance(model, ClipDetector):
        return list(model.head.parameters())
    for attr in ("classifier", "fc"):
        if hasattr(model, attr):
            layer = getattr(model, attr)
            last = [l for l in layer.modules() if isinstance(l, nn.Linear)][-1] if attr == "classifier" else layer
            return list(last.parameters())
    raise ValueError("no head found")

# ===== data download =====
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



# ===== synthetic document tampering =====
import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def rand_box(w, h, lo=0.04, hi=0.18):
    bw, bh = int(w * random.uniform(lo, hi)), int(h * random.uniform(lo / 2, hi / 2))
    x, y = random.randint(0, max(1, w - bw - 1)), random.randint(0, max(1, h - bh - 1))
    return x, y, x + bw, y + bh


def copy_move(img, _others):
    w, h = img.size
    b = rand_box(w, h)
    patch = img.crop(b)
    x, y = random.randint(0, w - patch.width), random.randint(0, h - patch.height)
    img.paste(patch, (x, y))


_FONTS = None


def _fonts():
    """Real TTF fonts found on the machine (Colab has DejaVu/Liberation). A single fixed font would become a 'fake' giveaway."""
    global _FONTS
    if _FONTS is None:
        import glob
        pats = ["/usr/share/fonts/**/*.ttf", "C:/Windows/Fonts/*.ttf", "/usr/local/lib/python3*/dist-packages/matplotlib/mpl-data/fonts/ttf/*.ttf"]
        _FONTS = sorted({f for p in pats for f in glob.glob(p, recursive=True)})
    return _FONTS


def erase_retype(img, _others):
    w, h = img.size
    x0, y0, x1, y1 = rand_box(w, h, 0.05, 0.2)
    # fill with the colour just around the box, not the whole-page average (looks more like a real cover-up)
    ring = [img.getpixel((min(max(x, 0), w - 1), min(max(y, 0), h - 1))) for x, y in ((x0 - 3, y0), (x1 + 3, y0), (x0, y0 - 3), (x0, y1 + 3))]
    bg = tuple(int(sum(c[i] for c in ring) / len(ring)) for i in range(3))
    d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x1, y1), fill=bg)
    size = max(10, int((y1 - y0) * random.uniform(0.6, 0.95)))
    font = None
    fonts = _fonts()
    for _ in range(3):
        try:
            font = ImageFont.truetype(random.choice(fonts), size) if fonts else None
            break
        except Exception:
            font = None
    if font is None:
        try:
            font = ImageFont.load_default(size)
        except TypeError:
            font = ImageFont.load_default()
    txt = "".join(random.choice("0123456789,./") for _ in range(random.randint(4, 10)))
    d.text((x0 + 2, y0), txt, fill=random.choice([(20, 20, 20), (0, 0, 0), (40, 40, 90), (60, 60, 60)]), font=font)


def splice(img, others):
    if not others:
        return copy_move(img, others)
    src = Image.open(random.choice(others)).convert("RGB")
    b = rand_box(*src.size)
    patch = src.crop(b)
    w, h = img.size
    img.paste(patch.resize((min(patch.width, w - 1), min(patch.height, h - 1))), (random.randint(0, max(1, w - patch.width)), random.randint(0, max(1, h - patch.height))))


def doc_fakes_main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--val_frac", type=float, default=0.15)
    ap.add_argument("--max_side", type=int, default=1200, help="downscale huge scans first")
    a = ap.parse_args(argv)
    random.seed(1)
    files = sorted(p for p in Path(a.real).rglob("*") if p.suffix.lower() in EXT)
    if len(files) < 20:
        raise SystemExit(f"Only {len(files)} images found; need at least a few hundred for useful training.")
    random.shuffle(files)
    nval = int(len(files) * a.val_frac)
    ops = [copy_move, erase_retype, splice]
    for i, p in enumerate(files):
        split = "val" if i < nval else "train"
        img = Image.open(p).convert("RGB")
        img.thumbnail((a.max_side, a.max_side))
        for cls in ("real", "fake"):
            (Path(a.out) / split / cls).mkdir(parents=True, exist_ok=True)
        base_q = random.randint(70, 95)
        img.save(Path(a.out) / split / "real" / f"{i:06d}.jpg", "JPEG", quality=base_q)
        fake = img.copy()
        for _ in range(random.randint(1, 2)):
            random.choice(ops)(fake, files)
        fake.save(Path(a.out) / split / "fake" / f"{i:06d}.jpg", "JPEG", quality=random.randint(60, 95))
    print(f"wrote {len(files) - nval} train / {nval} val pairs to {a.out}")



# ===== training =====
import argparse
import io
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms as T

EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def list_split(root: Path):
    items = []
    for label, name in ((0, "real"), (1, "fake")):
        d = root / name
        items += [(p, label) for p in sorted(d.rglob("*")) if p.suffix.lower() in EXT] if d.exists() else []
    return items


class JpegNoise:
    """Re-compress like WhatsApp/social upload so the model doesn't rely on a pristine-file artefact."""
    def __init__(self, p=0.5):
        self.p = p

    def __call__(self, img):
        if random.random() > self.p:
            return img
        b = io.BytesIO()
        img.save(b, "JPEG", quality=random.randint(55, 95))
        return Image.open(io.BytesIO(b.getvalue())).convert("RGB")


class DS(Dataset):
    def __init__(self, items, tf):
        self.items, self.tf = items, tf

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        p, y = self.items[i]
        try:
            img = Image.open(p).convert("RGB")
        except Exception:
            return self.__getitem__(random.randrange(len(self)))
        return self.tf(img), torch.tensor(float(y))


def auc(scores, labels):
    """Rank-based ROC-AUC, no sklearn needed."""
    s, y = np.asarray(scores), np.asarray(labels)
    pos, neg = (y == 1).sum(), (y == 0).sum()
    if pos == 0 or neg == 0:
        return float("nan")
    order = s.argsort()
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    return float((ranks[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


@torch.no_grad()
def evaluate(model, loader, dev):
    model.eval()
    sc, lb = [], []
    for x, y in loader:
        sc += torch.sigmoid(model(x.to(dev)).squeeze(1)).cpu().tolist()
        lb += y.tolist()
    sc, lb = np.array(sc), np.array(lb)
    # operating threshold = best balanced accuracy on val
    best_t, best_ba = 0.5, 0
    for t in np.linspace(0.05, 0.95, 91):
        pred = sc >= t
        ba = ((pred[lb == 1]).mean() + (~pred[lb == 0]).mean()) / 2
        if ba > best_ba:
            best_t, best_ba = float(t), float(ba)
    return {"auc": auc(sc, lb), "balanced_acc": best_ba, "threshold": best_t,
            "real_acc@thr": float((sc[lb == 0] < best_t).mean()), "fake_acc@thr": float((sc[lb == 1] >= best_t).mean())}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=TASKS, required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arch")
    ap.add_argument("--size", type=int)
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--freeze_epochs", type=int, default=1, help="train only the head first")
    ap.add_argument("--backbone_lr_mult", type=float, default=0.1, help="backbone LR = lr * this once unfrozen")
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--max_per_class", type=int, default=0, help="cap images per class (quick test)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no_pretrained", action="store_true", help="skip ImageNet weights (offline smoke tests)")
    a = ap.parse_args(argv)

    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    arch, size = a.arch or TASKS[a.task][0], a.size or TASKS[a.task][1]
    MEAN, STD = norm_for(arch)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    root = Path(a.data)

    if (root / "train").exists():
        tr_items, va_items = list_split(root / "train"), list_split(root / "val")
    else:
        allit = list_split(root)
        random.shuffle(allit)
        k = int(len(allit) * 0.85)
        tr_items, va_items = allit[:k], allit[k:]
    if a.max_per_class:
        cap = lambda it: [x for l in (0, 1) for x in [z for z in it if z[1] == l][: a.max_per_class]]  # noqa: E731
        tr_items, va_items = cap(tr_items), cap(va_items)
    n_fake = sum(y for _, y in tr_items)
    print(f"task={a.task} arch={arch} size={size} device={dev} train={len(tr_items)} (fake {n_fake}) val={len(va_items)}")
    if n_fake == 0 or n_fake == len(tr_items) or not va_items:
        sys.exit("Need both real/ and fake/ images in train and val.")

    # Augmentations deliberately avoid heavy resize/blur: they erase the very artefacts we detect.
    tf_tr = T.Compose([JpegNoise(0.5), T.RandomResizedCrop(size, scale=(0.6, 1.0), ratio=(0.8, 1.25)), T.RandomHorizontalFlip(),
                       T.ColorJitter(0.15, 0.15, 0.1), T.ToTensor(), T.Normalize(MEAN, STD)])
    tf_va = T.Compose([T.Resize((size, size)), T.ToTensor(), T.Normalize(MEAN, STD)])
    a.bs = max(2, min(a.bs, len(tr_items) // 2))  # never leave zero batches on small datasets
    dl_tr = DataLoader(DS(tr_items, tf_tr), a.bs, shuffle=True, num_workers=a.workers, pin_memory=True, drop_last=True)
    dl_va = DataLoader(DS(va_items, tf_va), a.bs * 2, num_workers=a.workers)

    model = build(arch, pretrained=not a.no_pretrained).to(dev)
    pos_w = torch.tensor([(len(tr_items) - n_fake) / n_fake], device=dev)  # class-imbalance weight
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_w)
    head = head_params(model)
    head_ids = {id(p) for p in head}
    backbone = [p for p in model.parameters() if id(p) not in head_ids]
    lrs = [a.lr, a.lr * a.backbone_lr_mult]  # gentle backbone LR protects pretrained features
    opt = torch.optim.AdamW([{"params": head}, {"params": backbone}], lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, lrs, total_steps=a.epochs * len(dl_tr))
    scaler = torch.cuda.amp.GradScaler(enabled=dev == "cuda")

    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    ckpt = out.with_suffix(".ckpt")
    start, best = 0, {"auc": -1}
    # A checkpoint is only resumed if it came from the SAME run settings; otherwise its LR schedule/weights don't apply.
    sig = {"task": a.task, "arch": arch, "size": size, "epochs": a.epochs, "bs": a.bs, "n_train": len(tr_items),
           "lr": a.lr, "freeze": a.freeze_epochs}
    if ckpt.exists():
        c = torch.load(ckpt, map_location=dev)
        if c.get("sig") == sig and c["epoch"] + 1 < a.epochs:
            model.load_state_dict(c["model"]); opt.load_state_dict(c["opt"]); sched.load_state_dict(c["sched"])
            start, best = c["epoch"] + 1, c["best"]
            print(f"resumed from epoch {start}")
        else:
            why = "already finished" if c.get("sig") == sig else "settings differ from this run"
            print(f"ignoring old checkpoint ({why}); starting fresh. The existing .pth at the output path will be overwritten.")
            best = {"auc": -1}

    for ep in range(start, a.epochs):
        for p in model.parameters():
            p.requires_grad = ep >= a.freeze_epochs or id(p) in head_ids
        model.train(); t0, tot = time.time(), 0.0
        for i, (x, y) in enumerate(dl_tr):
            x, y = x.to(dev), y.to(dev)
            with torch.autocast(dev, enabled=dev == "cuda"):
                loss = loss_fn(model(x).squeeze(1), y)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
            tot += loss.item()
            if i % 50 == 0:
                print(f"  ep{ep} it{i}/{len(dl_tr)} loss {loss.item():.4f}", flush=True)
        m = evaluate(model, dl_va, dev)
        print(f"epoch {ep}: train_loss {tot / len(dl_tr):.4f} | val AUC {m['auc']:.4f} bal.acc {m['balanced_acc']:.4f} "
              f"(thr {m['threshold']:.2f}) | {time.time() - t0:.0f}s", flush=True)
        if m["auc"] > best["auc"]:
            best = m
            torch.save({"state_dict": model.state_dict(), "arch": arch, "img_size": size, "task": a.task,
                        "threshold": m["threshold"], "metrics": m, "mean": MEAN, "std": STD, "label_fake": 1}, out)
            print(f"  saved best -> {out}")
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(), "epoch": ep, "best": best,
                    "sig": sig}, ckpt)

    print("DONE. Best validation metrics:\n" + json.dumps(best, indent=2))
    print("\nIMPORTANT: val is from the same source as train. Test on a separate dataset/generator before trusting it.")




# ======================================================= entry point =======================================================
PRESET = {  # epochs, batch, head lr, backbone lr multiplier, frozen-backbone epochs
    "face":     dict(epochs=10, bs=16, lr=5e-4, mult=0.2,  freeze=1),
    "scene":    dict(epochs=8,  bs=64, lr=1e-3, mult=0.01, freeze=3),
    "document": dict(epochs=12, bs=16, lr=3e-4, mult=0.2,  freeze=1),
}


def _cli_args():
    """In a notebook, sys.argv holds kernel arguments or leftovers from an earlier run: ignore it. In `!python` mode use it."""
    return [] if ("ipykernel" in sys.modules or "google.colab" in sys.modules) else sys.argv[1:]


def run():
    import argparse
    import types
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default=TASK)
    ap.add_argument("--quick", action="store_true", default=QUICK_TEST)
    ap.add_argument("--full", action="store_true", help="real run (overrides --quick / QUICK_TEST)")
    ap.add_argument("--per_class", type=int, default=PER_CLASS)
    ap.add_argument("--data", help="skip download: use this existing folder (train/val/real/fake)")
    ap.add_argument("--out")
    ap.add_argument("--no_pretrained", action="store_true")
    cli, _ = ap.parse_known_args(_cli_args())
    if cli.full:
        cli.quick = False
    task, per_class = cli.task, (300 if cli.quick else cli.per_class)
    cfg = dict(PRESET[task])
    if cli.quick:
        cfg["epochs"], cfg["freeze"] = 1, 0   # quick test: train the whole network so the score means something

    out = cli.out
    if not out:
        base = "/content"
        try:
            from google.colab import drive
            drive.mount("/content/drive")
            base = "/content/drive/MyDrive/proofyx"
        except Exception:
            print("Google Drive not mounted: saving to /content (download it before the session ends)")
        out = f"{base}/{task}{'_quick' if cli.quick else ''}.pth"  # quick tests never touch the real model file
    data_dir = cli.data or f"/content/data_{task}"

    if not cli.data:
        print(f"== downloading data for {task} ==")
        ns = types.SimpleNamespace(out=data_dir, per_class=per_class, quick=cli.quick, repo="pujanpaudel/deepfake_face_classification")
        if task == "scene":
            scene(ns)
        elif task == "face":
            faces(ns)
        else:
            ns.out = "/content/real_docs"
            docs(ns)
            doc_fakes_main(["--real", "/content/real_docs", "--out", data_dir])

    targv = ["--task", task, "--data", data_dir, "--out", out, "--epochs", str(cfg["epochs"]), "--bs", str(cfg["bs"]),
                "--lr", str(cfg["lr"]), "--backbone_lr_mult", str(cfg["mult"]), "--freeze_epochs", str(cfg["freeze"]),
                "--workers", "2"] + (["--no_pretrained"] if cli.no_pretrained else [])
    if cli.quick:
        targv += ["--max_per_class", "300"]
    print("== training ==")
    main(targv)
    print(f"Saved: {out}")
    try:
        from google.colab import files
        files.download(out)
    except Exception:
        pass


if __name__ == "__main__":  # also true inside a Colab cell; protects Windows DataLoader workers
    run()
