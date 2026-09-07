#!/usr/bin/env python3
"""
СИЛА И ЧЕСТЬ — тизер v2, собранный в визуальном языке Mini App «ВОРОЖБИТОВ».

Палитра, типографика и UI-элементы взяты один в один из miniapp/styles.css:
  --bg #0b0b0d, --ink #f2f0eb, --muted #969593, --red #ff3e26, --acid #d9ff4a
  topbar с brand-mark (красный скошенный квадрат «V»), eyebrow с pulse-dot,
  H1 900 weight / line-height .83 / letter-spacing -.085em с красным <em>,
  image-index «01 / 09», image-stamp «NO REPEAT», красный ticker-бегунок,
  карточка товара с кнопками, финальный красный join-banner.

Кадры (1080x1920, 30 fps) генерируются PIL+numpy и потоком уходят в ffmpeg.
Запуск: python3 video/make_video.py  (~3 мин на 2 ядрах)
"""
from __future__ import annotations

import math
import subprocess
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # pragma: no cover
    FFMPEG = "ffmpeg"

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "video"
INTER = OUT_DIR / "fonts" / "Inter.ttf"          # variable: opsz 14..32, wght 100..900
STAR_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")  # ✳ для тикера

import os

MODE = os.environ.get("SIC_MODE", "teaser")           # teaser | hero
if MODE == "hero":
    W, H = 720, 924                                   # 3:4 (~.78) под .hero-visual Mini App
else:
    W, H = 1080, 1920
FPS = 30

# ---- палитра Mini App ------------------------------------------------------
BG = (11, 11, 13)
INK = (242, 240, 235)
MUTED = (150, 149, 147)
DIM = (94, 93, 96)
RED = (255, 62, 38)
ACID = (217, 255, 74)
WHITE = (255, 253, 247)
LEAD = (193, 191, 187)
TICKER_TXT = (9, 9, 9)

M = 64            # боковой отступ (app: clamp(20px,5vw,78px))
TICKER_H = 48     # высота бегунка (app: 40px)

# --------------------------------------------------------------------- script
# (файл, kicker, строка 1 (ink), строка 2 (red), сек, движение, фокус x,y)
SHOTS = [
    ("sila-i-chest-07-geliks.jpg",          "01 / ГЕЛИКИ ЗА СПИНОЙ",  "НОЧЬ.",    "СВОЙ ГОРОД.", 2.8, "pull_out",  (0.50, 0.32)),
    ("sila-i-chest-02-crew.jpg",            "02 / СВОИ",              "СВОИ",     "ЗА СПИНОЙ.",  2.5, "push_in",   (0.50, 0.42)),
    ("sila-i-chest-08-dog.jpg",             "03 / БЕЗ ЛИШНИХ СЛОВ",   "ОДИН",     "ВЗГЛЯД.",     2.7, "pan_left",  (0.72, 0.42)),
    ("sila-i-chest-03-gym.jpg",             "04 / ЖЕЛЕЗО",            "ЖЕЛЕЗО",   "НЕ ВРЁТ.",    2.5, "push_in",   (0.50, 0.38)),
    ("sila-i-chest-09-ring.jpg",            "05 / УГОЛ РИНГА",        "МЕЖДУ",    "РАУНДАМИ.",   2.7, "push_in",   (0.45, 0.36)),
    ("sila-i-chest-10-forge.jpg",           "06 / КУЗНИЦА",           "ХАРАКТЕР", "КУЁТСЯ.",     2.8, "push_in",   (0.52, 0.40)),
    ("sila-i-chest-04-boxing-back.jpg",     "07 / СПИНА",             "МЕЧ",      "ПО СПИНЕ.",   2.7, "pan_down",  (0.50, 0.30)),
    ("sila-i-chest-05-roof.jpg",            "08 / ГОРОД",             "ДЕРЖИМ",   "ТЕМП.",       2.5, "pan_right", (0.50, 0.45)),
    ("sila-i-chest-11-geliks-vertical.jpg", "09 / В ПОЛНЫЙ РОСТ",     "НЕ ДЛЯ",   "ВСЕХ.",       2.9, "push_in",   (0.50, 0.36)),
    ("sila-i-chest-12-grusha.jpg",          "10 / ГРУША",             "ГРУША",    "МАЛЕНЬКАЯ.",  2.6, "push_in",   (0.50, 0.52)),
]
PRODUCT_IMG = "sila-i-chest-06-flatlay.jpg"
INTRO_SEC = 2.8
PRODUCT_SEC = 3.4
OUTRO_SEC = 3.4
WIPE_FRAMES = 8   # длительность шторки между сегментами
TOTAL_INDEX = len(SHOTS) + 1  # 9 кадров + карточка товара

TICKER_ITEMS = ["MADE FOR THE ONES WHO KNOW", "DROP 001 / SMALL BATCH", "WEAR YOUR SIGNAL"]
TICKER_SPEED = 150.0  # px/s


# ---------------------------------------------------------------- typography
@lru_cache(maxsize=None)
def font(size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(INTER), size)
    opsz = max(14, min(32, size / 2.6))
    f.set_variation_by_axes([opsz, weight])
    return f


@lru_cache(maxsize=None)
def star_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(STAR_FONT), size)


def text_w(text: str, fnt: ImageFont.FreeTypeFont, tracking: float = 0.0) -> float:
    if not text:
        return 0.0
    return fnt.getlength(text) + tracking * fnt.size * (len(text) - 1)


def draw_tracked(d: ImageDraw.ImageDraw, xy, text: str, fnt: ImageFont.FreeTypeFont, fill,
                 tracking: float = 0.0, align: str = "left") -> float:
    """Текст с letter-spacing (в em), базовая линия в xy[1]. Возвращает ширину."""
    x, y = xy
    total = text_w(text, fnt, tracking)
    if align == "right":
        x -= total
    elif align == "center":
        x -= total / 2
    if abs(tracking) < 1e-6:
        d.text((x, y), text, font=fnt, fill=fill, anchor="ls")
        return total
    for i, ch in enumerate(text):
        d.text((x, y), ch, font=fnt, fill=fill, anchor="ls")
        x += fnt.getlength(text[: i + 1]) - fnt.getlength(text[:i]) + tracking * fnt.size
    return total


def ease(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def stage(t: float, start: float, dur: float = 0.35) -> float:
    return ease_out((t - start) / dur)


def rgba(col, a: float):
    return (*col, int(255 * min(1.0, max(0.0, a))))


# ------------------------------------------------------------- UI primitives
def brand_lockup(layer: Image.Image, x: int, y: int, a: float, dark: bool = False) -> None:
    """brand-mark (скошенный квадрат) + ВОРОЖБИТОВ / SHOP / 001."""
    size = 86
    mark_bg, mark_fg = (BG, RED) if dark else (RED, TICKER_TXT)
    sq = Image.new("RGBA", (size + 30, size), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sq)
    ds.rectangle((15, 0, 15 + size, size), fill=rgba(mark_bg, a))
    draw_tracked(ds, (15 + size / 2 + 2, size * 0.76), "V", font(54, 900), rgba(mark_fg, a), align="center")
    k = math.tan(math.radians(9))
    sq = sq.transform(sq.size, Image.AFFINE, (1, k, -k * size / 2, 0, 1, 0), resample=Image.BICUBIC)
    layer.alpha_composite(sq, (x - 15, y))
    d = ImageDraw.Draw(layer)
    tx = x + size + 30
    col = BG if dark else INK
    colm = (60, 60, 62) if dark else MUTED
    draw_tracked(d, (tx, y + 40), "ВОРОЖБИТОВ", font(33, 800), rgba(col, a), tracking=0.13)
    draw_tracked(d, (tx, y + 70), "SHOP / 001", font(22, 600), rgba(colm, a), tracking=0.20)


def icon_button(d: ImageDraw.ImageDraw, x: int, y: int, kind: str, a: float) -> None:
    s = 92
    d.rectangle((x, y, x + s, y + s), outline=rgba(INK, 0.16 * a), width=2)
    c = rgba(INK, a)
    cx, cy = x + s / 2, y + s / 2
    if kind == "bookmark":
        d.line([(cx - 16, cy - 20), (cx + 16, cy - 20), (cx + 16, cy + 22), (cx, cy + 10), (cx - 16, cy + 22), (cx - 16, cy - 20)], fill=c, width=4, joint="curve")
    else:  # bag
        d.rectangle((cx - 20, cy - 8, cx + 20, cy + 22), outline=c, width=4)
        d.arc((cx - 12, cy - 24, cx + 12, cy + 2), 180, 360, fill=c, width=4)


def button(d: ImageDraw.ImageDraw, x: int, y: int, label: str, a: float, style: str = "primary") -> int:
    """Кнопка Mini App: 45px→124px, 10px/800/.13em → 28px, стрелка ↗ 18px→50px. Возвращает ширину."""
    hgt, pad, gap = 124, 50, 40
    f_lbl, f_arr = font(28, 800), font(50, 400)
    arrow = label[-1] if label[-1] in "↗↓" else ""
    text = label[:-1].rstrip() if arrow else label
    wl = text_w(text, f_lbl, 0.13)
    wa = f_arr.getlength(arrow) if arrow else 0
    total = int(pad + wl + (gap + wa if arrow else 0) + pad)
    if style == "primary":
        d.rectangle((x, y, x + total, y + hgt), fill=rgba(RED, a))
        col = arrow_col = TICKER_TXT
    elif style == "dark":
        d.rectangle((x, y, x + total, y + hgt), fill=rgba(BG, a))
        col = arrow_col = INK
    elif style == "ghost":
        d.rectangle((x, y, x + total, y + hgt), fill=rgba(WHITE, 0.05 * a), outline=rgba(WHITE, 0.25 * a), width=2)
        col = arrow_col = INK
    else:  # outline-on-red
        d.rectangle((x, y, x + total, y + hgt), fill=rgba(BG, 0.05 * a), outline=rgba(BG, 0.45 * a), width=2)
        col = arrow_col = BG
    by = y + hgt / 2 + 10
    draw_tracked(d, (x + pad, by), text, f_lbl, rgba(col, a), tracking=0.13)
    if arrow:
        d.text((x + pad + wl + gap, by + 2), arrow, font=f_arr, fill=rgba(arrow_col, a), anchor="ls")
    return total


def kicker(d: ImageDraw.ImageDraw, x: int, baseline: int, text: str, a: float, col=MUTED, align="left") -> None:
    draw_tracked(d, (x, baseline), text, font(28, 600), rgba(col, a), tracking=0.14, align=align)


def headline(d: ImageDraw.ImageDraw, x: int, baseline: int, text: str, size: int, col, a: float, dy: float = 0.0) -> None:
    """H1/H2 Mini App: 900 weight, letter-spacing -.085em."""
    draw_tracked(d, (x - size * 0.04, baseline + dy), text, font(size, 900), rgba(col, a), tracking=-0.085)


def fit_size(lines: tuple[str, ...], max_size: int, max_w: int) -> int:
    size = max_size
    while size > 90 and max(text_w(l, font(size, 900), -0.085) for l in lines) > max_w:
        size -= 4
    return size


def headline_block(d: ImageDraw.ImageDraw, l1: str, l2: str, a1: float, a2: float,
                   max_size: int, baseline2: int, col1=INK, col2=RED) -> None:
    size = fit_size((l1, l2), max_size, W - 2 * M)
    pitch = int(size * 0.83)  # line-height .83
    headline(d, M, baseline2 - pitch, l1, size, col1, a1, dy=60 * (1 - a1))
    headline(d, M, baseline2, l2, size, col2, a2, dy=60 * (1 - a2))


def image_index(d: ImageDraw.ImageDraw, x: int, baseline: int, cur: int, total: int, a: float) -> None:
    f = font(30, 600)
    w1 = draw_tracked(d, (x, baseline), f"{cur:02d}", f, rgba(WHITE, a), tracking=0.12)
    w2 = draw_tracked(d, (x + w1 + 14, baseline), "/", f, rgba(RED, a))
    draw_tracked(d, (x + w1 + 14 + w2 + 14, baseline), f"{total:02d}", f, rgba(WHITE, a), tracking=0.12)


def image_stamp(d: ImageDraw.ImageDraw, right: int, baseline: int, a: float) -> None:
    f = font(28, 900)
    draw_tracked(d, (right, baseline), "NO", f, rgba(ACID, a), tracking=0.10, align="right")
    draw_tracked(d, (right, baseline + 27), "REPEAT", f, rgba(ACID, a), tracking=0.10, align="right")


def corner_label(d: ImageDraw.ImageDraw, x: int, bottom: int, l1: str, l2: str, a: float) -> None:
    f = font(22, 600)
    w = max(text_w(l1, f, 0.12), text_w(l2, f, 0.12))
    top = bottom - 2 * 30 - 2 * 19
    d.rectangle((x, top, x + w + 2 * 25, bottom), outline=rgba(WHITE, 0.3 * a), width=2)
    draw_tracked(d, (x + 25, top + 19 + 22), l1, f, rgba(WHITE, a), tracking=0.12)
    draw_tracked(d, (x + 25, top + 19 + 22 + 30), l2, f, rgba(RED, a), tracking=0.12)


def pulse_dot(d: ImageDraw.ImageDraw, cx: int, cy: int, t: float, a: float) -> None:
    ring = 11 + 4 * math.sin(t * 2 * math.pi * 1.1)
    d.ellipse((cx - 10 - ring, cy - 10 - ring, cx + 10 + ring, cy + 10 + ring), fill=rgba(RED, 0.14 * a))
    d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=rgba(RED, a))


# ------------------------------------------------------------------- ticker
_ticker_cache: dict[bool, tuple[Image.Image, int]] = {}


def ticker_strip(inverted: bool) -> tuple[Image.Image, int]:
    if inverted in _ticker_cache:
        return _ticker_cache[inverted]
    bg, fg = (BG, RED) if inverted else (RED, TICKER_TXT)
    f = font(25, 900)
    sf = star_font(40)
    gap = 58
    items_w = [text_w(s, f, 0.16) for s in TICKER_ITEMS]
    star_w = sf.getlength("✳")
    period = int(sum(items_w) + len(items_w) * (star_w + 2 * gap))
    reps = math.ceil(W / period) + 2
    strip = Image.new("RGB", (period * reps, TICKER_H), bg)
    d = ImageDraw.Draw(strip)
    x = 0.0
    by = TICKER_H / 2 + 9
    for _ in range(reps):
        for s, wds in zip(TICKER_ITEMS, items_w):
            draw_tracked(d, (x, by), s, f, fg, tracking=0.16)
            x += wds + gap
            d.text((x, by + 4), "✳", font=sf, fill=fg, anchor="ls")
            x += star_w + gap
    _ticker_cache[inverted] = (strip, period)
    return strip, period


def paste_ticker(frame: Image.Image, abs_frame: int, inverted: bool = False) -> None:
    t = abs_frame / FPS
    slide = 1 - ease(min(1.0, max(0.0, (t - 0.45) / 0.4)))  # выезжает снизу на интро
    if slide >= 1.0:
        return
    strip, period = ticker_strip(inverted)
    off = int(t * TICKER_SPEED) % period
    band = strip.crop((off, 0, off + W, TICKER_H))
    y = H - TICKER_H + int(TICKER_H * slide)
    frame.paste(band, (0, y))


# --------------------------------------------------------------- image ops
def cover_crop(img: Image.Image, zoom: float, cx: float, cy: float, size=(W, H)) -> Image.Image:
    tw, th = size
    iw, ih = img.size
    base = max(tw / iw, th / ih)
    scale = base * zoom
    cw, ch = tw / scale, th / scale
    x0 = min(max(cx * iw - cw / 2, 0), iw - cw)
    y0 = min(max(cy * ih - ch / 2, 0), ih - ch)
    return img.resize((tw, th), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))


def motion(kind: str, t: float, focus: tuple[float, float]) -> tuple[float, float, float]:
    e = ease(t)
    fx, fy = focus
    if kind == "push_in":
        return 1.0 + 0.12 * e, fx, fy
    if kind == "pull_out":
        return 1.14 - 0.12 * e, fx, fy
    if kind == "pan_down":
        return 1.08, fx, fy + 0.30 * e
    if kind == "pan_right":
        return 1.08, fx - 0.08 + 0.16 * e, fy
    if kind == "pan_left":
        return 1.03, fx - 0.26 * e, fy
    return 1.0, fx, fy


_vig: Image.Image | None = None


def vignette() -> Image.Image:
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _vig = Image.fromarray((np.clip((r - 0.55) / 0.9, 0, 1) ** 1.6 * 0.82 * 255).astype(np.uint8), "L")
    return _vig


def grade(frame: Image.Image, rng: np.random.Generator) -> Image.Image:
    """Грейд как в приложении: contrast(1.05) saturate(.72) + зерно + виньетка."""
    arr = np.asarray(frame, dtype=np.float32) / 255.0
    arr = np.clip((arr - 0.5) * 1.07 + 0.5, 0, 1)
    lum = arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    arr = lum[..., None] + (arr - lum[..., None]) * 0.74
    arr[..., 2] += (1 - lum) * 0.03
    arr[..., 0] += lum * 0.015
    arr += rng.normal(0, 0.016, size=(H, W, 1)).astype(np.float32)
    np.clip(arr, 0, 1, out=arr)
    out = Image.fromarray((arr * 255).astype(np.uint8), "RGB")
    return Image.composite(Image.new("RGB", (W, H), (5, 5, 7)), out, vignette())


def flat_noise(img: Image.Image, rng: np.random.Generator, sigma: float = 3.5) -> Image.Image:
    arr = np.asarray(img, dtype=np.float32) + rng.normal(0, sigma, size=(H, W, 1))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


_grad: Image.Image | None = None


def bottom_gradient(alpha: float) -> Image.Image:
    global _grad
    if _grad is None:
        gh = 820
        g = Image.new("L", (1, gh))
        for y in range(gh):
            g.putpixel((0, y), int(215 * (y / (gh - 1)) ** 1.3))
        _grad = g.resize((W, gh))
    dark = Image.new("RGBA", (W, _grad.height), (*BG, 255))
    dark.putalpha(_grad.point(lambda v: int(v * alpha)))
    return dark


# ---------------------------------------------------------------- segments
def render_intro(rng, start_frame: int):
    n = int(INTRO_SEC * FPS)
    for i in range(n):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        # topbar
        a0 = stage(t, 0.0)
        brand_lockup(layer, M, 40, a0)
        d = ImageDraw.Draw(layer)
        icon_button(d, W - M - 92, 37, "bag", a0)
        icon_button(d, W - M - 92 - 14 - 92, 37, "bookmark", a0)
        d.line((0, 166, W, 166), fill=rgba(INK, 0.08 * a0), width=2)
        # eyebrow
        a1 = stage(t, 0.25)
        pulse_dot(d, M + 10, 606, t, a1)
        kicker(d, M + 42, 616, "DROP 001 / LIMITED RUN", a1)
        draw_tracked(d, (W - M, 616), "09—26", font(28, 800), rgba(RED, a1), tracking=0.14, align="right")
        # h1 — как в hero: НЕ ДЛЯ / ВСЕХ.
        headline_block(d, "НЕ ДЛЯ", "ВСЕХ.", stage(t, 0.4, 0.45), stage(t, 0.55, 0.45), 250, 1068)
        # hero-lead
        a4 = stage(t, 0.8, 0.4)
        fl = font(36, 400)
        d.text((M, 1160), "Городская форма для тех, кто сам", font=fl, fill=rgba(LEAD, a4), anchor="ls")
        d.text((M, 1216), "выбирает, что носить. Никаких повторов.", font=fl, fill=rgba(LEAD, a4), anchor="ls")
        # hero-actions
        a5 = stage(t, 1.0, 0.4)
        bw = button(d, M, 1290, "СМОТРЕТЬ ДРОП ↗", a5, "primary")
        draw_tracked(d, (M + bw + 60, 1290 + 62 + 10), "О КОНЦЕПЦИИ", font(28, 700), rgba(MUTED, a5), tracking=0.10)
        d.text((M + bw + 60 + text_w("О КОНЦЕПЦИИ", font(28, 700), 0.10) + 12, 1290 + 62 + 12), "↓", font=font(40, 400), fill=rgba(RED, a5), anchor="ls")
        # hero-specs
        a6 = stage(t, 1.15, 0.45)
        d.line((M, 1520, M + 900, 1520), fill=rgba(INK, 0.16 * a6), width=2)
        for j, (big, small) in enumerate((("001", "LIMITED DROP"), ("02", "ПРИНТА"), ("RU", "MADE FOR CITY"))):
            x = M + j * 300
            draw_tracked(d, (x, 1612), big, font(66, 900), rgba(INK, a6), tracking=-0.07)
            draw_tracked(d, (x, 1652), small, font(22, 600), rgba(MUTED, a6), tracking=0.12)
        frame = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
        frame = flat_noise(frame, rng)
        paste_ticker(frame, start_frame + i)
        yield frame


def render_shot(img: Image.Image, spec, rng, index: int, start_frame: int):
    _, kick, l1, l2, dur, kind, focus = spec
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        zoom, cx, cy = motion(kind, i / max(n - 1, 1), focus)
        frame = grade(cover_crop(img, zoom, cx, cy), rng).convert("RGBA")
        frame.alpha_composite(bottom_gradient(0.82), (0, H - 820))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        a0 = stage(t, 0.0, 0.3)
        image_index(d, M, 124, index, TOTAL_INDEX, a0)
        image_stamp(d, W - M, 118, a0)
        kicker(d, M, 1392, kick, stage(t, 0.05, 0.35))
        headline_block(d, l1, l2, stage(t, 0.12, 0.45), stage(t, 0.26, 0.45), 210, 1772)
        frame = Image.alpha_composite(frame, layer).convert("RGB")
        paste_ticker(frame, start_frame + i)
        yield frame


def render_product(img: Image.Image, rng, start_frame: int):
    """Карточка товара из витрины Mini App: image-frame + index/stamp/corner-label + кнопки."""
    n = int(PRODUCT_SEC * FPS)
    card = (M, 340, W - M, 340 + (W - 2 * M))
    cw = card[2] - card[0]
    for i in range(n):
        t = i / FPS
        base = Image.new("RGB", (W, H), BG)
        z = 1.0 + 0.06 * ease(i / max(n - 1, 1))
        pic = cover_crop(img, z, 0.5, 0.5, size=(cw, cw))
        arr = np.asarray(pic, dtype=np.float32) / 255.0
        lum = arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        arr = np.clip((lum[..., None] + (arr - lum[..., None]) * 0.72 - 0.5) * 1.05 + 0.5, 0, 1)
        pic = Image.fromarray((arr * 255).astype(np.uint8), "RGB")
        base.paste(pic, (card[0], card[1]))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        a0 = stage(t, 0.0, 0.3)
        kicker(d, M, 300, "01 / ВИТРИНА", a0)
        draw_tracked(d, (W - M, 300), "1 ПОЗИЦИЯ", font(28, 600), rgba(MUTED, a0), tracking=0.14, align="right")
        d.rectangle(card, outline=rgba(INK, 0.16 * a0), width=2)
        # image-frame overlays
        image_index(d, card[0] + 40, card[1] + 66, TOTAL_INDEX, TOTAL_INDEX, a0)
        image_stamp(d, card[2] - 40, card[1] + 60, a0)
        corner_label(d, card[0] + 40, card[3] - 40, "CORE UNIT", "V—001", a0)
        # теги над футболками
        for k, (fx, label, t0) in enumerate(((0.25, "ПЕРЕД", 0.55), (0.75, "СПИНА", 0.8))):
            aa = stage(t, t0, 0.3)
            x = int(card[0] + cw * fx) - 100
            y = card[1] + 128
            d.rectangle((x, y, x + 200, y + 64), fill=rgba(BG, 0.88 * aa))
            d.rectangle((x, y, x + 6, y + 64), fill=rgba(RED, aa))
            draw_tracked(d, (x + 28, y + 44), label, font(28, 800), rgba(WHITE, aa), tracking=0.13)
        # product-info
        a1 = stage(t, 0.3, 0.4)
        draw_tracked(d, (M, card[3] + 84), "ФУТБОЛКА «СИЛА И ЧЕСТЬ»", font(46, 800), rgba(INK, a1), tracking=-0.03)
        kicker(d, M, card[3] + 136, "ЧЁРНАЯ · ПРИНТ НА ГРУДИ · МЕЧ И «ВВ» НА СПИНЕ", a1)
        a2 = stage(t, 0.55, 0.4)
        bw = button(d, M, card[3] + 190, "СМОТРЕТЬ ДРОП ↗", a2, "primary")
        button(d, M + bw + 16, card[3] + 190, "РАЗМЕРЫ ↓", a2, "ghost")
        frame = Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")
        frame = flat_noise(frame, rng, 3.0)
        paste_ticker(frame, start_frame + i)
        yield frame


def render_outro(rng, start_frame: int):
    """join-banner: красный фон, H2 (bg + ink), кнопки, footer-brand."""
    n = int(OUTRO_SEC * FPS)
    for i in range(n):
        t = i / FPS
        img = Image.new("RGB", (W, H), RED)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        a0 = stage(t, 0.15, 0.4)
        kicker(d, M, 700, "04 / ЗАКРЫТЫЙ СИГНАЛ", 0.58 * a0, col=BG)
        headline_block(d, "СИЛА", "И ЧЕСТЬ.", stage(t, 0.3, 0.45), stage(t, 0.45, 0.45), 240, 1140, col1=BG, col2=INK)
        a3 = stage(t, 0.7, 0.4)
        fp = font(36, 400)
        d.text((M, 1236), "Размер и цена — в боте.", font=fp, fill=rgba(BG, 0.72 * a3), anchor="ls")
        d.text((M, 1290), "Новые дропы и возвраты размеров — в канале.", font=fp, fill=rgba(BG, 0.72 * a3), anchor="ls")
        a4 = stage(t, 0.9, 0.4)
        bw = button(d, M, 1370, "ОТКРЫТЬ БОТА ↗", a4, "dark")
        button(d, M + bw + 16, 1370, "ПОДЕЛИТЬСЯ ↗", a4, "outline")
        a5 = stage(t, 1.1, 0.4)
        d.line((M, 1640, W - M, 1640), fill=rgba(BG, 0.25 * a5), width=2)
        brand_lockup(layer, M, 1690, a5, dark=True)
        d = ImageDraw.Draw(layer)
        draw_tracked(d, (W - M, 1745), "VOROZHBITOV / 2026", font(22, 600), rgba(BG, 0.6 * a5), tracking=0.20, align="right")
        frame = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
        frame = flat_noise(frame, rng, 2.5)
        paste_ticker(frame, start_frame + i, inverted=True)
        yield frame


# ------------------------------------------------------------- transitions
def wipe(old: Image.Image, new: Image.Image, p: float) -> Image.Image:
    """Шторка слева направо с красной кромкой (цвет тикера/кнопок)."""
    x = int(W * p)
    out = old.copy()
    if x > 0:
        out.paste(new.crop((0, 0, x, H)), (0, 0))
    band = 46
    d = ImageDraw.Draw(out)
    d.rectangle((x, 0, min(W, x + band), H), fill=RED)
    return out


def fade(old: Image.Image, new: Image.Image, p: float) -> Image.Image:
    """Мягкий кроссфейд для hero-loop: без красной вертикальной полосы."""
    return Image.blend(old, new, p)


# -------------------------------------------------------------------- audio
def build_audio(total_sec: float, cut_times: list[float], path: Path, fade_end: float) -> None:
    """Ambient: низкий гул + дождь + sub-удар на каждой склейке + подъём перед финалом."""
    sr = 44100
    n = int(total_sec * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(7)
    drone = 0.17 * np.sin(2 * np.pi * 48 * t) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.11 * t))
    drone += 0.07 * np.sin(2 * np.pi * 96 * t + 0.5)
    rain = rng.normal(0, 1, n)
    low = np.convolve(rain, np.ones(24) / 24, mode="same")
    rain = (rain - low) * 0.03
    audio = drone + rain
    # пульс 92 bpm, тихо
    beat = 60 / 92
    k = 0
    while k * beat < total_sec:
        i0 = int(k * beat * sr)
        dur = int(0.22 * sr)
        if i0 + dur < n:
            tt = np.arange(dur) / sr
            freq = 58 * np.exp(-tt * 9) + 40
            audio[i0:i0 + dur] += np.sin(2 * np.pi * np.cumsum(freq) / sr) * np.exp(-tt * 14) * (0.30 if k % 2 == 0 else 0.16)
        k += 1
    for ct in cut_times:
        i0 = int(ct * sr)
        dur = int(0.55 * sr)
        if i0 + dur > n:
            continue
        tt = np.arange(dur) / sr
        freq = 72 * np.exp(-tt * 6) + 38
        audio[i0:i0 + dur] += np.sin(2 * np.pi * np.cumsum(freq) / sr) * np.exp(-tt * 7) * 0.7
        # короткий «щелчок шторки»
        click = rng.normal(0, 1, int(0.03 * sr)) * np.linspace(1, 0, int(0.03 * sr)) ** 2 * 0.25
        audio[i0:i0 + len(click)] += click
    # riser перед финальной склейкой
    if cut_times:
        last = cut_times[-1]
        i1 = int(last * sr)
        i0 = max(0, i1 - int(2.2 * sr))
        seg = rng.normal(0, 1, i1 - i0)
        env = np.linspace(0, 1, i1 - i0) ** 2.2 * 0.22
        audio[i0:i1] += seg * env
    fade = int(0.8 * sr)
    audio[:fade] *= np.linspace(0, 1, fade)
    end = int(fade_end * sr)
    tail_len = int(1.6 * sr)
    audio[end - tail_len:end] *= np.linspace(1, 0, tail_len)
    audio[end:] = 0
    audio = np.clip(audio / max(1e-6, np.abs(audio).max()) * 0.85, -1, 1)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())


# ------------------------------------------------------------------- encode
class FrameSink:
    """Пишет кадры напрямую в stdin ffmpeg — память не растёт с длиной ролика."""

    def __init__(self, out: Path, audio: Path, total_frames: int):
        self.n = 0
        # ВАЖНО: без "-shortest" — в ffmpeg 7 он буферизует до 10 с сырых кадров
        # (~930 МБ на 1080x1920) и словил OOM. Длительность задаём точно через -t.
        duration = f"{total_frames / FPS:.3f}"
        self.proc = subprocess.Popen(
            [
                FFMPEG, "-y", "-loglevel", "warning",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0",
                "-i", str(audio),
                "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
                "-threads", "2", "-x264-params", "rc-lookahead=10:bframes=2:ref=2:sync-lookahead=0:threads=2",
                "-thread_queue_size", "8",
                "-profile:v", "high", "-level", "4.1", "-movflags", "+faststart",
                "-c:a", "aac", "-b:a", "160k", "-t", duration,
                str(out),
            ],
            stdin=subprocess.PIPE, stderr=open(OUT_DIR / "_ffmpeg.log", "w"), bufsize=0,
        )

    def push(self, frame: Image.Image) -> None:
        self.proc.stdin.write(frame.tobytes())
        self.n += 1

    def close(self) -> int:
        self.proc.stdin.close()
        return self.proc.wait()


# --------------------------------------------------------------------- plan
def segment_lengths() -> list[int]:
    return [int(INTRO_SEC * FPS)] + [int(s[4] * FPS) for s in SHOTS] + [int(PRODUCT_SEC * FPS), int(OUTRO_SEC * FPS)]


def plan() -> tuple[list[int], list[float], float]:
    """Стартовые кадры сегментов (с учётом перекрытия шторок), времена склеек, длительность."""
    lengths = segment_lengths()
    starts, cuts = [], []
    pos = 0
    for j, ln in enumerate(lengths):
        if j > 0:
            pos -= WIPE_FRAMES
            cuts.append((pos + WIPE_FRAMES / 2) / FPS)
        starts.append(pos)
        pos += ln
    return starts, cuts, pos / FPS


HERO_SHOTS = [0, 1, 2, 9, 6, 8]  # гелики, свои, пёс, груша (вместо «железа» и «кузницы»), спина, рост — без ринга


def render_hero_shot(img: Image.Image, spec, rng, index: int, total: int):
    """Кадр hero-loop: наезд + kicker + двухстрочный заголовок. Без тикера и топбара."""
    _, kick, l1, l2, dur, kind, focus = spec
    n = int(dur * FPS)
    hm = int(M * W / 1080)                       # отступ в масштабе
    for i in range(n):
        t = i / FPS
        zoom, cx, cy = motion(kind, i / max(n - 1, 1), focus)
        frame = grade(cover_crop(img, zoom, cx, cy), rng).convert("RGBA")
        g = bottom_gradient(0.78)
        g = g.resize((W, int(g.height * H / 1920)))
        frame.alpha_composite(g, (0, H - g.height))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        # без счётчиков «04 / 07» и штампа NO REPEAT — по фидбеку они лишние
        size = fit_size((l1, l2), int(126 * W / 1080), W - 2 * hm)
        pitch = int(size * 0.83)
        a1, a2 = stage(t, 0.12, 0.45), stage(t, 0.26, 0.45)
        base2 = H - 44
        kicker(d, hm, base2 - 2 * pitch - 14, kick, stage(t, 0.05, 0.35))
        headline(d, hm, base2 - pitch, l1, size, INK, a1, dy=40 * (1 - a1))
        headline(d, hm, base2, l2, size, RED, a2, dy=40 * (1 - a2))
        yield Image.alpha_composite(frame, layer).convert("RGB")


def segments_hero(rng):
    picks = [SHOTS[k] for k in HERO_SHOTS]
    for idx, spec in enumerate(picks, start=1):
        img = Image.open(ROOT / spec[0]).convert("RGB")
        yield render_hero_shot(img, spec, rng, idx, len(picks))


class SilentSink(FrameSink):
    """Без аудио, CRF повыше, level 4.0 — под WebView и быстрый старт."""

    def __init__(self, out: Path, total_frames: int):
        self.n = 0
        self.proc = subprocess.Popen(
            [
                FFMPEG, "-y", "-loglevel", "warning",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0",
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "27", "-maxrate", "3M", "-bufsize", "6M",
                "-pix_fmt", "yuv420p", "-threads", "2",
                "-x264-params", "rc-lookahead=10:bframes=2:ref=2:sync-lookahead=0:threads=2:keyint=60:min-keyint=30",
                "-thread_queue_size", "8", "-profile:v", "high", "-level", "4.0", "-movflags", "+faststart",
                "-t", f"{total_frames / FPS:.3f}", str(out),
            ],
            stdin=subprocess.PIPE, stderr=open(OUT_DIR / "_ffmpeg.log", "w"), bufsize=0,
        )


def main_hero() -> None:
    """Hero-loop для Mini App: 720x924, ~16 с, без звука, шов цикла — шторкой."""
    rng = np.random.default_rng(5)
    lengths = [int(SHOTS[k][4] * FPS) for k in HERO_SHOTS]
    total_frames = sum(lengths) - WIPE_FRAMES * len(lengths)   # шторка и на стыке конец→начало
    out = OUT_DIR / "sila-i-chest-hero-loop.mp4"
    sink = SilentSink(out, total_frames)
    k = WIPE_FRAMES
    first_head: list[Image.Image] = []
    tail: list[Image.Image] = []
    for seg_no, gen in enumerate(segments_hero(rng)):
        it = iter(gen)
        head = [next(it) for _ in range(k)]
        if seg_no == 0:
            first_head = head          # первые k кадров отложим: цикл замкнётся кроссфейдом из хвоста
        else:
            for i in range(k):
                sink.push(fade(tail[i], head[i], ease((i + 1) / (k + 1))))
        buf: list[Image.Image] = []
        for fr in it:
            buf.append(fr)
            if len(buf) > k:
                sink.push(buf.pop(0))
        tail = buf
        print(f"hero segment {seg_no} done, frames {sink.n}", flush=True)
    for i in range(k):                 # шов: хвост последнего → голова первого
        sink.push(fade(tail[i], first_head[i], ease((i + 1) / (k + 1))))
    code = sink.close()
    if code != 0:
        raise SystemExit(f"ffmpeg exited with {code}")
    poster = OUT_DIR / "sila-i-chest-hero-poster.jpg"
    first_head[k - 1].save(poster, quality=82, optimize=True)
    print(f"frames: {sink.n}  duration: {sink.n / FPS:.1f}s")
    print("written:", out, f"{out.stat().st_size / 1024 / 1024:.2f} MB; poster:", poster)


def segments(rng, starts: list[int]):
    yield render_intro(rng, starts[0])
    for idx, spec in enumerate(SHOTS, start=1):
        img = Image.open(ROOT / spec[0]).convert("RGB")
        yield render_shot(img, spec, rng, idx, starts[idx])
    yield render_product(Image.open(ROOT / PRODUCT_IMG).convert("RGB"), rng, starts[len(SHOTS) + 1])
    yield render_outro(rng, starts[len(SHOTS) + 2])


def main() -> None:
    rng = np.random.default_rng(1)
    starts, cuts, total = plan()
    print(f"planned duration: {total:.1f}s, cuts at {[round(c, 2) for c in cuts]}", flush=True)
    audio_path = OUT_DIR / "_ambient.wav"
    build_audio(total + 2.0, cuts, audio_path, fade_end=total)
    out = OUT_DIR / "sila-i-chest-teaser.mp4"
    total_frames = sum(segment_lengths()) - WIPE_FRAMES * (len(segment_lengths()) - 1)
    sink = FrameSink(out, audio_path, total_frames)
    k = WIPE_FRAMES
    tail: list[Image.Image] = []
    for seg_no, gen in enumerate(segments(rng, starts)):
        it = iter(gen)
        if tail:
            head = [next(it) for _ in range(k)]
            for i in range(k):
                sink.push(wipe(tail[i], head[i], ease((i + 1) / (k + 1))))
        buf: list[Image.Image] = []
        for fr in it:
            buf.append(fr)
            if len(buf) > k:
                sink.push(buf.pop(0))
        tail = buf
        print(f"segment {seg_no} done, frames so far {sink.n}", flush=True)
    for fr in tail:
        sink.push(fr)
    code = sink.close()
    audio_path.unlink(missing_ok=True)
    if code != 0:
        raise SystemExit(f"ffmpeg exited with {code}")
    print(f"frames: {sink.n}  duration: {sink.n / FPS:.1f}s")
    print("written:", out, f"{out.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main_hero() if MODE == "hero" else main()
