"""Собирает вертикальный teaser 1080x1920 (Reels / Stories / Telegram) из кадров серии.

Запуск из корня sila-i-chest/:
    python3 video/make_video.py

Пайплайн: Pillow + numpy рендерят кадры (Ken Burns, грейн, виньетка,
типографика), ffmpeg из imageio-ffmpeg кодирует в H.264 + добавляет
ambient-звук, синтезированный numpy (низкий гул + удары на монтажных склейках).
"""
from __future__ import annotations

import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:  # pragma: no cover
    FFMPEG = "ffmpeg"

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "video"
FRAMES = OUT_DIR / "_frames"
FONT_PATH = OUT_DIR / "fonts" / "Oswald.ttf"

W, H = 1080, 1920
FPS = 30
RED = (214, 31, 38)
WHITE = (242, 242, 240)
MUTE = (141, 141, 136)

# --------------------------------------------------------------------- script
# (файл, заголовок, подпись, длительность сек, тип движения, фокус-точка x,y 0..1)
SHOTS = [
    # горизонтальные исходники 1109x960 -> вертикальное окно; фокус на лице (cx, cy)
    ("sila-i-chest-01-gelik-night.jpg", "НОЧЬ.", "ФОНАРИ / МОКРЫЙ АСФАЛЬТ", 3.2, "push_in", (0.5, 0.45)),
    ("sila-i-chest-02-crew.jpg", "СВОИ.", "ОДИН ВПЕРЕДИ / ОСТАЛЬНЫЕ ЗА СПИНОЙ", 3.0, "pull_out", (0.5, 0.45)),
    ("sila-i-chest-03-gym.jpg", "ЖЕЛЕЗО.", "МЕЖДУ ПОДХОДАМИ", 2.8, "push_in", (0.5, 0.42)),
    ("sila-i-chest-04-boxing-back.jpg", "СПИНА.", "ТУРНИК / МЕЧ ПО ПОЗВОНОЧНИКУ", 3.4, "pan_down", (0.5, 0.35)),
    ("sila-i-chest-05-roof.jpg", "ГОРОД.", "СИНИЙ ЧАС", 2.8, "pan_right", (0.5, 0.45)),
]
INTRO_SEC = 1.6
PRODUCT_SEC = 3.2
OUTRO_SEC = 2.6
XFADE = 0.35  # секунд плавного перехода между кадрами


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def ease(t: float) -> float:
    return t * t * (3 - 2 * t)  # smoothstep


def cover_crop(img: Image.Image, zoom: float, cx: float, cy: float) -> Image.Image:
    """Вырезает 9:16 окно из изображения с масштабом zoom вокруг точки (cx, cy)."""
    iw, ih = img.size
    base = max(W / iw, H / ih)
    scale = base * zoom
    cw, ch = W / scale, H / scale
    x0 = min(max(cx * iw - cw / 2, 0), iw - cw)
    y0 = min(max(cy * ih - ch / 2, 0), ih - ch)
    box = (x0, y0, x0 + cw, y0 + ch)
    return img.resize((W, H), Image.LANCZOS, box=box)


def motion(kind: str, t: float, focus: tuple[float, float]) -> tuple[float, float, float]:
    e = ease(t)
    fx, fy = focus
    if kind == "push_in":
        return 1.0 + 0.12 * e, fx, fy
    if kind == "pull_out":
        return 1.14 - 0.12 * e, fx, fy
    if kind == "pan_down":
        return 1.10, fx, 0.30 + 0.30 * e
    if kind == "pan_right":
        return 1.08, 0.42 + 0.16 * e, fy
    return 1.0, fx, fy


_vignette_cache: Image.Image | None = None


def vignette() -> Image.Image:
    global _vignette_cache
    if _vignette_cache is None:
        yy, xx = np.mgrid[0:H, 0:W]
        nx = (xx - W / 2) / (W / 2)
        ny = (yy - H / 2) / (H / 2)
        r = np.sqrt(nx ** 2 + ny ** 2)
        mask = np.clip((r - 0.55) / 0.9, 0, 1) ** 1.6 * 0.82
        _vignette_cache = Image.fromarray((mask * 255).astype(np.uint8), "L")
    return _vignette_cache


def grade(frame: Image.Image, rng: np.random.Generator) -> Image.Image:
    """Кинематографичный грейд: контраст, приглушённые тени, зерно, виньетка."""
    arr = np.asarray(frame, dtype=np.float32) / 255.0
    # лёгкий S-curve контраст
    arr = np.clip((arr - 0.5) * 1.08 + 0.5, 0, 1)
    # холодные тени / тёплые света
    lum = arr.mean(axis=2, keepdims=True)
    arr[..., 2] += (1 - lum[..., 0]) * 0.035  # синий в тени
    arr[..., 0] += lum[..., 0] * 0.02  # красный в свет
    # зерно
    arr += rng.normal(0, 0.016, size=(H, W, 1)).astype(np.float32)
    np.clip(arr, 0, 1, out=arr)
    out = Image.fromarray((arr * 255).astype(np.uint8), "RGB")
    black = Image.new("RGB", (W, H), (5, 5, 7))
    return Image.composite(black, out, vignette())


def draw_text_layer(title: str, sub: str, alpha: float, index: str) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    # нижний градиент под текст
    grad = Image.new("L", (1, 520))
    for y in range(520):
        grad.putpixel((0, y), int(200 * (y / 519) ** 1.4))
    grad = grad.resize((W, 520))
    dark = Image.new("RGBA", (W, 520), (5, 5, 7, 255))
    dark.putalpha(grad.point(lambda v: int(v * alpha)))
    layer.alpha_composite(dark, (0, H - 520))
    # индекс сверху слева
    d.text((64, 96), index, font=font(30), fill=(*MUTE, a))
    d.rectangle((64, 140, 64 + 60, 143), fill=(*RED, a))
    # заголовок
    d.text((64, H - 470), title, font=font(190), fill=(*WHITE, a))
    # подпись
    d.text((92, H - 190), sub, font=font(34), fill=(*MUTE, a))
    # красный маркер
    d.rectangle((64, H - 192, 64 + 8, H - 140), fill=(*RED, a))
    return layer


def render_shot(img: Image.Image, spec, rng, index_label: str, out_frames: list[Image.Image]) -> None:
    _, title, sub, dur, kind, focus = spec
    n = int(dur * FPS)
    for i in range(n):
        t = i / max(n - 1, 1)
        zoom, cx, cy = motion(kind, t, focus)
        frame = cover_crop(img, zoom, cx, cy)
        frame = grade(frame, rng)
        # текст появляется на 0.25с, уходит на последние 0.4с
        tin = min(1.0, (i / FPS) / 0.35)
        tout = min(1.0, ((n - i) / FPS) / 0.45)
        alpha = ease(min(tin, tout))
        if alpha > 0:
            frame = Image.alpha_composite(frame.convert("RGBA"), draw_text_layer(title, sub, alpha, index_label)).convert("RGB")
        out_frames.append(frame)


def render_intro(rng):
    n = int(INTRO_SEC * FPS)
    for i in range(n):
        t = i / (n - 1)
        img = Image.new("RGB", (W, H), (11, 11, 13))
        d = ImageDraw.Draw(img)
        # красная линия растёт
        line_w = int(W * 0.62 * ease(min(1, t * 1.6)))
        d.rectangle((64, 940, 64 + line_w, 946), fill=RED)
        a = ease(min(1, max(0, (t - 0.25) / 0.45)))
        col = tuple(int(c * a + 11 * (1 - a)) for c in WHITE)
        d.text((64, 700), "ВОРОЖБИТОВ", font=font(120), fill=col)
        colm = tuple(int(c * a + 11 * (1 - a)) for c in MUTE)
        d.text((66, 980), "DROP 001 / ФУТБОЛКА", font=font(36), fill=colm)
        arr = np.asarray(img, dtype=np.float32)
        arr = np.clip(arr + rng.normal(0, 4, size=(H, W, 1)), 0, 255)
        yield (Image.fromarray(arr.astype(np.uint8)))


def render_product(img: Image.Image, rng):
    """Раскладка: медленный наезд, затем два тега 'ПЕРЕД' / 'СПИНА'."""
    n = int(PRODUCT_SEC * FPS)
    for i in range(n):
        t = i / (n - 1)
        frame = cover_crop(img, 1.0, 0.5, 0.40)
        frame = grade(frame, rng)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        a = int(255 * ease(min(1, t / 0.3)))
        d.text((64, 96), "06 / 06", font=font(30), fill=(*MUTE, a))
        d.rectangle((64, 140, 124, 143), fill=(*RED, a))
        # теги с задержкой
        a1 = int(255 * ease(min(1, max(0, (t - 0.18) / 0.25))))
        a2 = int(255 * ease(min(1, max(0, (t - 0.38) / 0.25))))
        for (x, label, aa) in ((150, "ПЕРЕД", a1), (W - 150 - 240, "СПИНА", a2)):
            d.rectangle((x, 1380, x + 240, 1450), fill=(11, 11, 13, int(aa * 0.9)))
            d.rectangle((x, 1380, x + 6, 1450), fill=(*RED, aa))
            d.text((x + 28, 1390), label, font=font(40), fill=(*WHITE, aa))
        a3 = int(255 * ease(min(1, max(0, (t - 0.5) / 0.3))))
        d.text((64, H - 330), "СИЛА И ЧЕСТЬ", font=font(120), fill=(*WHITE, a3))
        d.text((92, H - 190), "100% ХЛОПОК · 240 Г/М² · S–XL", font=font(34), fill=(*MUTE, a3))
        d.rectangle((64, H - 192, 72, H - 140), fill=(*RED, a3))
        yield (Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB"))


def render_outro(rng):
    n = int(OUTRO_SEC * FPS)
    for i in range(n):
        t = i / (n - 1)
        img = Image.new("RGB", (W, H), (11, 11, 13))
        d = ImageDraw.Draw(img)
        a = ease(min(1, t / 0.35))
        col = tuple(int(c * a + 11 * (1 - a)) for c in WHITE)
        colr = tuple(int(c * a + 11 * (1 - a)) for c in RED)
        colm = tuple(int(c * a + 11 * (1 - a)) for c in MUTE)
        d.text((64, 640), "СИЛА", font=font(230), fill=col)
        d.text((64, 860), "И ЧЕСТЬ.", font=font(230), fill=colr)
        d.rectangle((64, 1140, 64 + int(W * 0.62 * a), 1146), fill=colr)
        a2 = ease(min(1, max(0, (t - 0.3) / 0.35)))
        colm2 = tuple(int(c * a2 + 11 * (1 - a2)) for c in MUTE)
        colw2 = tuple(int(c * a2 + 11 * (1 - a2)) for c in WHITE)
        d.text((66, 1180), "DROP 001 / ТИРАЖ ОГРАНИЧЕН", font=font(38), fill=colm2)
        d.text((66, 1250), "ЗАБРАТЬ РАЗМЕР — В БОТЕ", font=font(46), fill=colw2)
        arr = np.asarray(img, dtype=np.float32)
        arr = np.clip(arr + rng.normal(0, 4, size=(H, W, 1)), 0, 255)
        yield (Image.fromarray(arr.astype(np.uint8)))


def crossfade(a: list[Image.Image], b: list[Image.Image], seconds: float) -> list[Image.Image]:
    k = min(int(seconds * FPS), len(a), len(b))
    if k <= 0:
        return a + b
    out = a[:-k]
    for i in range(k):
        t = ease((i + 1) / (k + 1))
        out.append(Image.blend(a[len(a) - k + i], b[i], t))
    return out + b[k:]


def hard_cut_flash(frames: list[Image.Image], at: int, strength: float = 0.35, length: int = 3) -> None:
    """Короткая белая вспышка на склейке — ритм."""
    for j in range(length):
        idx = at + j
        if 0 <= idx < len(frames):
            s = strength * (1 - j / length)
            frames[idx] = Image.blend(frames[idx], Image.new("RGB", (W, H), (250, 245, 240)), s)


def build_audio(total_sec: float, cut_times: list[float], path: Path, fade_end: float | None = None) -> None:
    """Ambient: низкий гул + sub-удары на склейках + лёгкий шум дождя."""
    sr = 44100
    n = int(total_sec * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(7)
    drone = 0.18 * np.sin(2 * np.pi * 48 * t) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.11 * t))
    drone += 0.08 * np.sin(2 * np.pi * 96 * t + 0.5)
    rain = rng.normal(0, 1, n)
    # фильтруем шум в «дождь» простым скользящим средним (низкие частоты) и вычитанием
    kernel = np.ones(24) / 24
    low = np.convolve(rain, kernel, mode="same")
    rain = (rain - low) * 0.035
    audio = drone + rain
    for ct in cut_times:
        i0 = int(ct * sr)
        dur = int(0.55 * sr)
        if i0 + dur > n:
            continue
        tt = np.arange(dur) / sr
        freq = 70 * np.exp(-tt * 6) + 38
        hit = np.sin(2 * np.pi * np.cumsum(freq) / sr) * np.exp(-tt * 7) * 0.75
        audio[i0:i0 + dur] += hit
    # фейды
    fade = int(0.8 * sr)
    audio[:fade] *= np.linspace(0, 1, fade)
    tail_len = int(1.5 * sr)
    end = int(fade_end * sr) if fade_end else n
    audio[end - tail_len:end] *= np.linspace(1, 0, tail_len)
    audio[end:] = 0
    audio = np.clip(audio / max(1e-6, np.abs(audio).max()) * 0.85, -1, 1)
    pcm = (audio * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


class FrameSink:
    """Пишет кадры напрямую в stdin ffmpeg — память не растёт с длиной ролика."""

    def __init__(self, out: Path, audio: Path):
        self.n = 0
        self.proc = subprocess.Popen(
            [
                FFMPEG, "-y", "-loglevel", "warning",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0",
                "-i", str(audio),
                "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
                "-threads", "2", "-x264-params", "rc-lookahead=10:bframes=2:ref=2:sync-lookahead=0:threads=2",
                "-thread_queue_size", "8",
                "-profile:v", "high", "-level", "4.1", "-movflags", "+faststart",
                "-c:a", "aac", "-b:a", "160k", "-shortest",
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


def segment_lengths() -> list[int]:
    lengths = [int(INTRO_SEC * FPS)]
    lengths += [int(spec[3] * FPS) for spec in SHOTS]
    lengths += [int(PRODUCT_SEC * FPS), int(OUTRO_SEC * FPS)]
    return lengths


def plan_cuts() -> tuple[list[float], float]:
    """Считает времена склеек и общую длительность без рендера (для аудио)."""
    lengths = segment_lengths()
    k = int(XFADE * FPS)
    cuts = [lengths[0] / FPS]
    pos = lengths[0]
    body_len = lengths[1]
    for seg_len in lengths[2:-1]:
        cuts.append((pos + body_len - k / 2) / FPS)
        body_len = body_len + seg_len - k
    pos += body_len
    cuts.append(pos / FPS)
    total = (pos + lengths[-1]) / FPS
    return cuts, total


def generators(rng):
    """Ленивая последовательность сегментов: каждый — генератор кадров."""
    yield "intro", render_intro(rng)
    for idx, spec in enumerate(SHOTS, start=1):
        img = Image.open(ROOT / spec[0]).convert("RGB")
        yield "shot", render_shot_iter(img, spec, rng, f"{idx:02d} / 06")
    yield "product", render_product_iter(Image.open(ROOT / "sila-i-chest-06-flatlay.jpg").convert("RGB"), rng)
    yield "outro", render_outro(rng)


def render_shot_iter(img, spec, rng, index_label: str):
    _, title, sub, dur, kind, focus = spec
    n = int(dur * FPS)
    for i in range(n):
        t = i / max(n - 1, 1)
        zoom, cx, cy = motion(kind, t, focus)
        frame = grade(cover_crop(img, zoom, cx, cy), rng)
        tin = min(1.0, (i / FPS) / 0.35)
        tout = min(1.0, ((n - i) / FPS) / 0.45)
        alpha = ease(min(tin, tout))
        if alpha > 0:
            frame = Image.alpha_composite(frame.convert("RGBA"), draw_text_layer(title, sub, alpha, index_label)).convert("RGB")
        yield frame


def render_product_iter(img, rng):
    for frame in render_product(img, rng):
        yield frame


def main() -> None:
    rng = np.random.default_rng(1)
    cuts, total = plan_cuts()
    print(f"planned duration: {total:.1f}s, cuts at {[round(c, 2) for c in cuts]}")

    audio_path = OUT_DIR / "_ambient.wav"
    build_audio(total + 2.0, cuts, audio_path, fade_end=total)  # wav длиннее видео; конец задаёт видео
    out = OUT_DIR / "sila-i-chest-teaser.mp4"
    sink = FrameSink(out, audio_path)
    k = int(XFADE * FPS)
    flash_at = {int(cuts[0] * FPS): 0.35, int(cuts[-1] * FPS): 0.25}

    def emit(frame: Image.Image) -> None:
        if sink.n in flash_at:
            s = flash_at[sink.n]
            frame = Image.blend(frame, Image.new("RGB", (W, H), (250, 245, 240)), s)
        elif (sink.n - 1) in flash_at:
            frame = Image.blend(frame, Image.new("RGB", (W, H), (250, 245, 240)), flash_at[sink.n - 1] * 0.5)
        sink.push(frame)

    tail: list[Image.Image] = []  # последние k кадров предыдущего shot-сегмента для crossfade
    for kind, gen in generators(rng):
        if kind in ("intro", "outro"):
            for fr in tail:
                emit(fr)
            tail = []
            for fr in gen:
                emit(fr)
            continue
        frames_iter = iter(gen)
        if tail:
            # смешиваем хвост предыдущего с головой текущего
            head = [next(frames_iter) for _ in range(k)]
            for i in range(k):
                emit(Image.blend(tail[i], head[i], ease((i + 1) / (k + 1))))
        buf: list[Image.Image] = []
        for fr in frames_iter:
            buf.append(fr)
            if len(buf) > k:
                emit(buf.pop(0))
        tail = buf  # ровно k кадров (или меньше, если сегмент короткий)
    for fr in tail:
        emit(fr)

    code = sink.close()
    audio_path.unlink(missing_ok=True)
    if code != 0:
        raise SystemExit(f"ffmpeg exited with {code}")
    print(f"frames: {sink.n}  duration: {sink.n / FPS:.1f}s")
    print("written:", out, f"{out.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
