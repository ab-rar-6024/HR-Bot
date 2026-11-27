"""Train one detector and save a .pth.  One run = one model = one Colab session / laptop.

Data layout (any of train/val, or a single folder that is split 85/15):
    DATA/train/real/*.jpg   DATA/train/fake/*.jpg   DATA/val/real   DATA/val/fake
Label convention: fake = 1.

    python training/train.py --task face --data /content/data_face --out /content/drive/MyDrive/proofyx/face.pth

Saved .pth is a dict: state_dict, arch, img_size, task, metrics, threshold. It resumes from <out>.ckpt after a Colab disconnect.
"""
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from training.models import TASKS, build, head_params, norm_for  # noqa: E402
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


if __name__ == "__main__":
    main()
