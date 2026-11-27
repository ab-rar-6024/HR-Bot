"""ProofyX DOCUMENT model.   (Runtime > Change runtime type > GPU)
SCRIPT MODE (recommended): upload this file to Colab (Files panel), then run in cells:
    from google.colab import drive; drive.mount('/content/drive')
    !python -u /content/train_document.py --quick        # few-minute test
    !python -u /content/train_document.py --full         # real run, 12 epochs
CELL MODE: paste the whole file into one cell and run it.
Trains a ConvNeXt-Tiny to spot tampered invoices / IDs. Saves document.pth to Google Drive (MyDrive/proofyx/) and downloads it.
First run with QUICK_TEST = True (few minutes), then set it to False for the real run."""
QUICK_TEST = True        # True = 300 pairs, 1 epoch. False = full run (12 epochs)
PER_CLASS = 6000         # max real documents to use (about 3,800 are available)
# ------------------------------------------------------------------------------------------------------------
import subprocess, sys, types
for _m, _p in (("huggingface_hub", "huggingface_hub"),):
    try:
        __import__(_m)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "-q", "install", _p])

# ===== model definitions =====
import torch
import torch.nn as nn
from torchvision import models

IMAGENET = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])

TASKS = {"document": ("convnext_tiny", 384, "tampered ID cards / invoices / scanned documents")}


def norm_for(arch: str):
    return IMAGENET


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
    else:
        raise ValueError(f"unknown arch {arch}")
    return m


def head_params(model: nn.Module):
    """The freshly initialised classifier layer (trained first while the backbone is frozen)."""
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
from pathlib import Path

from PIL import Image

random.seed(0)
EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def save(img: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "JPEG", quality=random.randint(70, 95))


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
CFG = dict(epochs=12, bs=16, lr=3e-4, mult=0.2, freeze=1)


def _cli_args():
    """In a notebook, sys.argv holds kernel arguments or leftovers from an earlier run: ignore it. In `!python` mode use it."""
    return [] if ("ipykernel" in sys.modules or "google.colab" in sys.modules) else sys.argv[1:]


def run():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", default=QUICK_TEST, help="small fast test run")
    ap.add_argument("--full", action="store_true", help="real run (overrides --quick / QUICK_TEST)")
    ap.add_argument("--epochs", type=int, help="override the number of epochs")
    ap.add_argument("--per_class", type=int, default=PER_CLASS)
    ap.add_argument("--real", help="use this folder of real document images instead of downloading")
    ap.add_argument("--out")
    ap.add_argument("--work", default="/content", help="working folder")
    ap.add_argument("--no_pretrained", action="store_true")
    cli, _ = ap.parse_known_args(_cli_args())
    if cli.full:
        cli.quick = False
    per_class = 300 if cli.quick else cli.per_class
    cfg = dict(CFG)
    if cli.quick:
        cfg["epochs"], cfg["freeze"] = 1, 0   # quick test: train the whole network so the score means something
    if cli.epochs:
        cfg["epochs"] = cli.epochs

    out = cli.out
    if not out:
        base = "/content"
        if Path("/content/drive/MyDrive").exists():           # Drive already mounted (do this in a separate notebook cell)
            base = "/content/drive/MyDrive/proofyx"
        else:
            try:                                              # works when pasted into a notebook cell
                from google.colab import drive
                drive.mount("/content/drive")
                base = "/content/drive/MyDrive/proofyx"
            except Exception:
                print("Google Drive not mounted: saving to /content (download it from the Files panel before the session ends)")
        out = f"{base}/document{'_quick' if cli.quick else ''}.pth"
    data_dir = f"{cli.work}/data_document"
    real_dir = cli.real or f"{cli.work}/real_docs"
    # Add your OWN real scans/invoices (ideally phone photos too) into real_dir for a better model.
    if not cli.real:
        print("== downloading real documents ==")
        docs(types.SimpleNamespace(out=real_dir, per_class=per_class))
    print("== making tampered copies ==")
    doc_fakes_main(["--real", real_dir, "--out", data_dir])

    targv = ["--task", "document", "--data", data_dir, "--out", out, "--epochs", str(cfg["epochs"]), "--bs", str(cfg["bs"]),
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


if __name__ == "__main__":
    run()
