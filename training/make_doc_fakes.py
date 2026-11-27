"""Build a document-tamper dataset from REAL document images (scans of IDs/invoices/receipts you are allowed to use).

    python training/make_doc_fakes.py --real /content/real_docs --out /content/data_document

Per real image it writes the original to real/ and a tampered copy to fake/ using one of:
  copy-move (duplicate a region elsewhere), erase+retype (blank a region, draw new digits/text),
  splice (paste a region from another document). The tampered copy is then JPEG-recompressed at a different
  quality than the original so double-compression artefacts exist in the fakes the way they do in real forgeries.
Real images are re-saved too, so the model cannot cheat on compression history. Split is by source image.
Synthetic fakes are easier than real forgeries: add real forged samples (from APM / fraud cases) as soon as you have them.
"""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--val_frac", type=float, default=0.15)
    ap.add_argument("--max_side", type=int, default=1200, help="downscale huge scans first")
    a = ap.parse_args()
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


if __name__ == "__main__":
    main()
