#!/usr/bin/env python3
"""Оптимизация фото для Mini App: кроп/чистка → размеры → WebP + JPEG → manifest.json.

Реальные фото товара (скриншоты из видео) проходят: denoise → баланс белого → тон → резкость.
Опция --isolate вырезает объект (GrabCut) и ставит его на «студийный» фон витрины (#0b0b0d).

  python3 tools/optimize_images.py --name tag-front --src ../sila-i-chest/real/src-tag-front.png \
      --crop 176,66,504,600 --denoise 5 --wb 0.7 --contrast 1.05 --saturation 0.92
  python3 tools/optimize_images.py --name bag --src ../sila-i-chest/real/src-bag.png --isolate 85,115,650,940 --denoise 3
  python3 tools/optimize_images.py --name crew --src ../sila-i-chest/sila-i-chest-02-crew.jpg   # только размеры

Результат: miniapp/assets/img/<name>-{480,800,1080}.{webp,jpg}, <name>.jpg (=800, для бота/Telegram)
и запись в miniapp/assets/img/manifest.json (размеры, srcset, LQIP-плейсхолдер).
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "miniapp" / "assets" / "img"
WIDTHS = (480, 800, 1080)
MAX_UPSCALE = 2.2  # скриншоты маленькие: тянем не больше чем в 2.2 раза


def parse_rect(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    x, y, w, h = (int(v) for v in value.split(","))
    return x, y, w, h


def gray_world(img: np.ndarray, strength: float) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[..., 1] -= (lab[..., 1].mean() - 128.0) * strength
    lab[..., 2] -= (lab[..., 2].mean() - 128.0) * strength
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def tone(img: np.ndarray, contrast: float, saturation: float) -> np.ndarray:
    x = np.clip((img.astype(np.float32) / 255.0 - 0.5) * contrast + 0.5, 0, 1)
    hsv = cv2.cvtColor(x, cv2.COLOR_BGR2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * saturation, 0, 1)
    return (cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR) * 255.0).round().astype(np.uint8)


def isolate(img: np.ndarray, rect: tuple[int, int, int, int]) -> np.ndarray:
    mask = np.zeros(img.shape[:2], np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(img, mask, rect, bgd, fgd, 6, cv2.GC_INIT_WITH_RECT)
    m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        m = np.where(labels == keep, 255, 0).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    return cv2.GaussianBlur(m, (0, 0), 1.4)


def studio_bg(h: int, w: int) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w * 0.72)) ** 2 + ((yy - h * 0.42) / (h * 0.78)) ** 2)
    base = np.array([0x0D, 0x0B, 0x0B], np.float32)   # BGR #0b0b0d
    high = np.array([0x20, 0x1C, 0x1C], np.float32)   # BGR #1c1c20
    t = np.clip(1.0 - d, 0, 1)[..., None] ** 1.4
    bg = base + (high - base) * t
    noise = np.random.default_rng(7).normal(0, 1.5, (h, w, 1)).astype(np.float32)
    return np.clip(bg + noise, 0, 255).astype(np.uint8)


def composite(img: np.ndarray, m: np.ndarray, aspect: float, pad: float = 0.11) -> np.ndarray:
    ys, xs = np.where(m > 8)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    obj, om = img[y0:y1, x0:x1].astype(np.float32), m[y0:y1, x0:x1].astype(np.float32) / 255.0
    oh, ow = om.shape
    cw = int(ow * (1 + 2 * pad))
    ch = int(round(cw / aspect))
    if ch < oh * (1 + 2 * pad):
        ch = int(oh * (1 + 2 * pad))
        cw = int(round(ch * aspect))
    canvas = studio_bg(ch, cw).astype(np.float32)
    ox, oy = (cw - ow) // 2, (ch - oh) // 2
    shadow = np.zeros((ch, cw), np.float32)
    sy = min(oy + int(oh * 0.035), ch - oh)
    shadow[sy:sy + oh, ox:ox + ow] = om
    shadow = cv2.GaussianBlur(shadow, (0, 0), max(6, ow * 0.045)) * 0.8
    canvas *= (1.0 - shadow)[..., None]
    region = canvas[oy:oy + oh, ox:ox + ow]
    canvas[oy:oy + oh, ox:ox + ow] = obj * om[..., None] + region * (1 - om[..., None])
    return np.clip(canvas, 0, 255).astype(np.uint8)


def export(name: str, img: np.ndarray) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    width, height = pil.size
    entry: dict = {"width": width, "height": height, "aspect": round(width / height, 4), "webp": [], "jpg": []}
    for w in WIDTHS:
        if w > width * MAX_UPSCALE:
            continue
        h = max(1, round(height * w / width))
        im = pil.resize((w, h), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55 if w <= width else 38, threshold=2))
        im.save(OUT / f"{name}-{w}.webp", "WEBP", quality=82, method=6)
        im.save(OUT / f"{name}-{w}.jpg", "JPEG", quality=84, optimize=True, progressive=True)
        entry["webp"].append([w, f"assets/img/{name}-{w}.webp"])
        entry["jpg"].append([w, f"assets/img/{name}-{w}.jpg"])
    default = 800 if any(w == 800 for w, _ in entry["jpg"]) else entry["jpg"][-1][0]
    shutil.copyfile(OUT / f"{name}-{default}.jpg", OUT / f"{name}.jpg")
    entry["src"] = f"assets/img/{name}.jpg"
    tiny = pil.resize((24, max(1, round(24 * height / width))), Image.LANCZOS)
    buf = io.BytesIO()
    tiny.save(buf, "WEBP", quality=40, method=6)
    entry["lqip"] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest[name] = entry
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return entry


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--crop", help="x,y,w,h")
    ap.add_argument("--isolate", help="x,y,w,h — прямоугольник GrabCut вокруг объекта (в координатах исходника)")
    ap.add_argument("--aspect", type=float, default=0.84, help="w/h холста для --isolate (карточка витрины = .84)")
    ap.add_argument("--denoise", type=float, default=0.0)
    ap.add_argument("--wb", type=float, default=0.0, help="сила gray-world баланса белого 0..1")
    ap.add_argument("--contrast", type=float, default=1.0)
    ap.add_argument("--saturation", type=float, default=1.0)
    args = ap.parse_args()

    img = cv2.imread(str((ROOT / args.src) if not Path(args.src).is_absolute() else args.src), cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"cannot read {args.src}")
    crop = parse_rect(args.crop)
    if crop:
        x, y, w, h = crop
        img = img[y:y + h, x:x + w]
    if args.denoise > 0:
        img = cv2.fastNlMeansDenoisingColored(img, None, args.denoise, args.denoise, 7, 21)
    if args.wb > 0:
        img = gray_world(img, args.wb)
    if args.contrast != 1.0 or args.saturation != 1.0:
        img = tone(img, args.contrast, args.saturation)
    iso = parse_rect(args.isolate)
    if iso:
        img = composite(img, isolate(img, iso), args.aspect)
    entry = export(args.name, img)
    print(f"{args.name}: {entry['width']}x{entry['height']} → {[w for w, _ in entry['jpg']]}")


if __name__ == "__main__":
    main()
