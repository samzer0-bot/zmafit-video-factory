"""شورتس متحرك بأسلوب "3D تشريحي" (مانيكان + عضلات متوهجة) — بدون لقطات جاهزة.

يرسم كل إطار برمجياً (numpy + PIL) بمُظلِّل 2.5D بسيط، ثم يضيف الترجمة العربية
(PIL + raqm)، والموسيقى المولَّدة، والتعليق الصوتي (edge-tts) إن كان متاحاً.

الاستعمال:
    python scripts/anim_short.py                 # مع الصوت إن توفر الاتصال
    python scripts/anim_short.py --no-voice      # موسيقى + ترجمة فقط
    python scripts/anim_short.py --workers 4 --out out/forearm.mp4
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import subprocess
import sys
import wave
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

W, H, FPS = 1080, 1920, 30
SS = 2                      # Supersampling للحواف الناعمة

# ---------------------------------------------------------------- السكربت
SCENES = [
    {   # 1) الخطّاف
        "kind": "hook", "min": 3.6,
        "narration": "تريد ساعدًا قويًا وقبضة حديدية؟ إليك هذا التمرين!",
        "title": "ساعد حديدي", "sub": "في 30 ثانية فقط",
    },
    {   # 2) شرح التمرين
        "kind": "exercise", "min": 8.0,
        "narration": "اجلس أمام البنش، وضع ساعديك عليه والرسغ خارج الحافة، "
                     "ثم ارفع الدمبل بثني الرسغ فقط.",
        "title": "تمرين ثني الرسغ", "sub": "WRIST CURL",
    },
    {   # 3) القبضة الخاطئة والصحيحة
        "kind": "grip", "min": 7.0,
        "narration": "انتبه للقبضة: لا تترك الإبهام مفتوحًا، بل لُفّه حول البار لتحمي رسغك.",
        "title": "القبضة الصحيحة", "left": "الإبهام مفتوح", "right": "الإبهام ملفوف",
    },
    {   # 4) المجموعات والإيقاع
        "kind": "sets", "min": 6.5,
        "narration": "نفّذ ثلاث مجموعات من خمس عشرة تكرارًا، وانزل ببطء لمدة ثانيتين.",
        "title": "3 × 15", "sub": "نزول بطيء: ثانيتان",
    },
    {   # 5) الدعوة للمتابعة
        "kind": "cta", "min": 3.6,
        "narration": "احفظ الفيديو وتابعنا للمزيد!",
        "title": "تابعنا للمزيد", "sub": None,
    },
]
TARGET = 30.0

# ---------------------------------------------------------------- الألوان
CLAY = np.array([0.80, 0.81, 0.84], np.float32)          # المانيكان
CLAY_DARK = CLAY * 0.78
MUSCLE = np.array([1.00, 0.45, 0.12], np.float32)        # العضلة المستهدفة
GRIP = np.array([1.00, 0.66, 0.16], np.float32)          # اليد (أصفر-برتقالي)
METAL = np.array([0.62, 0.64, 0.68], np.float32)
IRON = np.array([0.20, 0.21, 0.23], np.float32)
BENCH = np.array([0.13, 0.13, 0.14], np.float32)
FRAME = np.array([0.30, 0.31, 0.33], np.float32)

KEY = np.array([-0.45, -0.65, 0.62], np.float32)
KEY /= np.linalg.norm(KEY)
HALF = KEY + np.array([0, 0, 1], np.float32)
HALF /= np.linalg.norm(HALF)


# ================================================================ المُظلِّل 2.5D
class Scene3D:
    """Z-buffer بسيط لأشكال منتفخة (كبسولات، إهليلجات، صناديق مستديرة)."""

    def __init__(self, w: int, h: int, scale: float = 1.0, off=(0.0, 0.0)):
        self.w, self.h = w * SS, h * SS
        self.k = scale * SS
        self.ox, self.oy = off[0] * SS, off[1] * SS
        self.z = np.full((self.h, self.w), -1e9, np.float32)
        self.n = np.zeros((self.h, self.w, 3), np.float32)
        self.alb = np.zeros((self.h, self.w, 3), np.float32)
        self.emi = np.zeros((self.h, self.w, 3), np.float32)
        self.spec = np.zeros((self.h, self.w), np.float32)

    # تحويل إحداثيات المشهد إلى بكسلات
    def _p(self, x, y):
        return x * self.k + self.ox, y * self.k + self.oy

    def _box(self, x0, y0, x1, y1):
        ix0 = max(int(math.floor(x0)), 0)
        iy0 = max(int(math.floor(y0)), 0)
        ix1 = min(int(math.ceil(x1)) + 1, self.w)
        iy1 = min(int(math.ceil(y1)) + 1, self.h)
        if ix1 <= ix0 or iy1 <= iy0:
            return None
        ys, xs = np.mgrid[iy0:iy1, ix0:ix1].astype(np.float32)
        return (slice(iy0, iy1), slice(ix0, ix1)), xs + 0.5, ys + 0.5

    def _write(self, sl, inside, depth, nx, ny, nz, col, spec, emissive, fiber=None):
        zb = self.z[sl]
        m = inside & (depth > zb)
        if not m.any():
            return
        zb[m] = depth[m]
        nn = self.n[sl]
        nn[..., 0][m] = nx[m]
        nn[..., 1][m] = ny[m]
        nn[..., 2][m] = nz[m]
        a = self.alb[sl]
        e = self.emi[sl]
        if fiber is not None:
            tex = (0.78 + 0.22 * fiber)[m][:, None]
        else:
            tex = 1.0
        a[m] = np.asarray(col)[None, :] * tex
        e[m] = (np.asarray(col)[None, :] * emissive * tex) if emissive else 0.0
        self.spec[sl][m] = spec

    def capsule(self, a, b, r0, r1, col, depth=0.0, spec=0.35, emissive=0.0, fibers=0):
        ax, ay = self._p(*a)
        bx, by = self._p(*b)
        r0, r1 = r0 * self.k, r1 * self.k
        R = max(r0, r1)
        box = self._box(min(ax, bx) - R, min(ay, by) - R, max(ax, bx) + R, max(ay, by) + R)
        if box is None:
            return
        sl, xs, ys = box
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy + 1e-6
        t = np.clip(((xs - ax) * dx + (ys - ay) * dy) / L2, 0, 1)
        cx, cy = ax + t * dx, ay + t * dy
        vx, vy = xs - cx, ys - cy
        d = np.sqrt(vx * vx + vy * vy)
        r = r0 + (r1 - r0) * t
        inside = d < r
        q = np.clip(d / r, 0, 1)
        nz = np.sqrt(np.clip(1 - q * q, 0, 1))
        fib = None
        if fibers:
            L = math.sqrt(L2)
            side = (vx * (-dy) + vy * dx) / L / np.maximum(r, 1)     # -1..1 عرضياً
            fib = 0.5 + 0.5 * np.sin(side * fibers + np.sin(t * 6) * 0.6)
        self._write(sl, inside, depth * self.k + r * nz, vx / np.maximum(r, 1e-3),
                    vy / np.maximum(r, 1e-3), nz, col, spec, emissive, fib)

    def ellipse(self, c, ra, rb, ang, col, depth=0.0, spec=0.35, emissive=0.0, fibers=0):
        cx, cy = self._p(*c)
        ra, rb = ra * self.k, rb * self.k
        R = max(ra, rb)
        box = self._box(cx - R, cy - R, cx + R, cy + R)
        if box is None:
            return
        sl, xs, ys = box
        ca, sa = math.cos(ang), math.sin(ang)
        px, py = xs - cx, ys - cy
        u = (px * ca + py * sa) / ra
        v = (-px * sa + py * ca) / rb
        q = u * u + v * v
        inside = q < 1
        nz = np.sqrt(np.clip(1 - q, 0, 1))
        nx_l, ny_l = u, v
        nx = nx_l * ca - ny_l * sa
        ny = nx_l * sa + ny_l * ca
        ln = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
        fib = None
        if fibers:
            fib = 0.5 + 0.5 * np.sin(v * fibers)
        self._write(sl, inside, depth * self.k + min(ra, rb) * nz, nx / ln, ny / ln, nz / ln,
                    col, spec, emissive, fib)

    def rbox(self, x0, y0, x1, y1, rad, col, depth=0.0, spec=0.25):
        X0, Y0 = self._p(x0, y0)
        X1, Y1 = self._p(x1, y1)
        rad = rad * self.k
        box = self._box(X0, Y0, X1, Y1)
        if box is None:
            return
        sl, xs, ys = box
        qx = np.clip(xs, X0 + rad, X1 - rad)
        qy = np.clip(ys, Y0 + rad, Y1 - rad)
        vx, vy = xs - qx, ys - qy
        d = np.sqrt(vx * vx + vy * vy)
        inside = d < rad
        q = np.clip(d / rad, 0, 1)
        nz = np.sqrt(np.clip(1 - q * q, 0, 1))
        self._write(sl, inside, depth * self.k + rad * nz, vx / rad, vy / rad, nz, col, spec, 0.0)

    # ------------------------------------------------ الإضاءة
    def shade(self, bg: np.ndarray, glow: float = 1.0, rim=(0.35, 0.55, 1.0)) -> np.ndarray:
        """bg: صورة خلفية float (h*SS, w*SS, 3) → صورة uint8 بالمقاس الأصلي."""
        cov = self.z > -1e8
        n = self.n
        diff = np.clip(n @ KEY, 0, 1)
        fill = np.clip(n @ np.array([0.6, -0.1, 0.8], np.float32), 0, 1) * 0.25
        sp = np.clip(n @ HALF, 0, 1) ** 28 * self.spec
        rimf = (1 - np.clip(n[..., 2], 0, 1)) ** 2.2 * np.clip(n[..., 0] * 0.8 - n[..., 1] * 0.3, 0, 1)
        col = self.alb * (0.16 + 0.9 * diff + fill)[..., None]
        col += sp[..., None]
        col += rimf[..., None] * np.array(rim, np.float32) * 0.85
        col += self.emi
        out = np.where(cov[..., None], col, bg)

        # توهج العضلات
        if glow > 0 and self.emi.any():
            e = np.clip(self.emi * 255, 0, 255).astype(np.uint8)
            small = Image.fromarray(e).resize((self.w // 8, self.h // 8), Image.BILINEAR)
            small = small.filter(ImageFilter.GaussianBlur(5))
            g = np.asarray(small.resize((self.w, self.h), Image.BILINEAR), np.float32) / 255
            out = out + g * 1.6 * glow
        out = np.clip(out, 0, 1)
        img = Image.fromarray((out * 255).astype(np.uint8))
        return np.asarray(img.resize((self.w // SS, self.h // SS), Image.LANCZOS))


# ================================================================ الخلفيات
@lru_cache(maxsize=8)
def panel_bg(w: int, h: int, tint=(0.10, 0.11, 0.14), spot=(0.5, 0.35)) -> np.ndarray:
    ys, xs = np.mgrid[0:h * SS, 0:w * SS].astype(np.float32)
    xs /= w * SS
    ys /= h * SS
    d = np.sqrt((xs - spot[0]) ** 2 * 1.4 + (ys - spot[1]) ** 2)
    v = np.clip(1.15 - d * 1.5, 0, 1)
    base = np.array(tint, np.float32)
    img = base[None, None, :] * (0.35 + 0.95 * v[..., None])
    # ظل أرضي ناعم
    fl = np.exp(-(((xs - 0.55) / 0.42) ** 2 + ((ys - 0.93) / 0.05) ** 2))
    img *= (1 - 0.55 * fl)[..., None]
    return img.astype(np.float32)


@lru_cache(maxsize=1)
def frame_bg() -> np.ndarray:
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xs - W / 2) / W) ** 2 + ((ys - H * 0.45) / H) ** 2)
    v = np.clip(1 - d * 1.35, 0, 1)
    c = 0.09 + 0.16 * v
    img = np.stack([c, c, c * 1.03], -1)
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def paste_panel(frame: Image.Image, img: np.ndarray, x: int, y: int, glow_col=(200, 200, 205),
                radius=26, border_alpha=1.0):
    """يلصق اللوحة بحواف مستديرة وإطار فضّي متوهج."""
    h, w = img.shape[:2]
    p = Image.fromarray(img)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    # توهج الإطار
    pad = 30
    gl = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    a = int(150 * border_alpha)
    gd.rounded_rectangle([pad - 3, pad - 3, w + pad + 2, h + pad + 2], radius + 3,
                         outline=glow_col + (a,), width=7)
    gl = gl.filter(ImageFilter.GaussianBlur(9))
    frame.alpha_composite(gl, (x - pad, y - pad)) if frame.mode == "RGBA" else \
        frame.paste(gl, (x - pad, y - pad), gl)
    frame.paste(p, (x, y), mask)
    bd = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    ImageDraw.Draw(bd).rounded_rectangle([1, 1, w + 6, h + 6], radius + 3,
                                         outline=glow_col + (int(235 * border_alpha),), width=4)
    frame.paste(bd, (x - 4, y - 4), bd)


# ================================================================ الشخصيات
def _rot(cx, cy, r, ang):
    return cx + r * math.cos(ang), cy + r * math.sin(ang)


def seated_figure(s: Scene3D, wrist: float, pulse: float):
    """رجل جالس جانبياً أمام بنش، الساعدان على البنش، والرسغ يتحرك (wrist بالراديان)."""
    # --- البنش (إطار X مثل المرجع)
    s.capsule((330, 760), (770, 1080), 20, 20, FRAME, depth=-40, spec=0.5)
    s.capsule((770, 760), (380, 1080), 20, 20, FRAME, depth=-60, spec=0.5)
    s.capsule((300, 1085), (860, 1085), 24, 24, FRAME, depth=-30, spec=0.5)
    s.capsule((540, 760), (540, 900), 26, 26, FRAME, depth=-50, spec=0.5)
    s.rbox(230, 690, 640, 770, 26, BENCH, depth=-10, spec=0.18)

    # --- الساق (ركبة على الأرض خلف البنش)
    s.capsule((150, 880), (250, 1040), 78, 58, CLAY_DARK, depth=-30)
    s.capsule((250, 1040), (40, 1080), 52, 38, CLAY_DARK, depth=-35)

    # --- الذراع الخلفية (أغمق وأبعد)
    off = (32, -22)
    def arm(dx, dy, dep, shade, glow):
        sh = (318 + dx, 548 + dy)
        el = (430 + dx, 680 + dy)
        wr = (668 + dx, 668 + dy)
        s.capsule(sh, el, 50, 40, CLAY * shade, depth=dep)
        s.capsule(el, wr, 46, 30, MUSCLE * shade, depth=dep + 4, spec=0.55,
                  emissive=glow, fibers=14)
        hx, hy = _rot(wr[0], wr[1], 70, wrist)
        s.capsule(wr, (hx, hy), 30, 30, CLAY * shade, depth=dep + 6)
        # الدمبل: الأقراص تُرى من الجانب كدائرة
        dx2, dy2 = _rot(wr[0], wr[1], 92, wrist)
        nx, ny = -math.sin(wrist), math.cos(wrist)        # فوق راحة اليد (الكف للأعلى)
        cx, cy = dx2 - nx * 30, dy2 - ny * 30
        s.ellipse((cx, cy), 60, 60, 0, IRON * 1.5 * shade, depth=dep - 26, spec=0.9)
        s.ellipse((cx, cy), 44, 44, 0, IRON * 1.1 * shade, depth=dep - 2, spec=0.7)
        s.ellipse((cx, cy), 22, 22, 0, METAL * shade, depth=dep + 30, spec=1.0)
        # الأصابع ملتفة حول المقبض
        fx, fy = _rot(wr[0], wr[1], 98, wrist)
        s.capsule((hx, hy), (fx - nx * 22, fy - ny * 22), 24, 20, CLAY * shade, depth=dep + 36)

    arm(*off, -20, 0.72, 0.35 * pulse)

    # --- الجذع والرأس
    s.ellipse((190, 830), 100, 80, -0.5, CLAY, depth=0)                 # الحوض
    s.capsule((200, 820), (290, 610), 80, 96, CLAY, depth=0)             # البطن/الصدر
    s.ellipse((325, 600), 112, 86, -0.85, CLAY, depth=34, spec=0.45)     # الصدر
    s.ellipse((265, 735), 62, 70, -0.5, CLAY, depth=30, spec=0.4)        # البطن
    s.ellipse((300, 545), 62, 56, 0, CLAY, depth=22)                     # الكتف
    s.capsule((345, 505), (392, 450), 42, 40, CLAY, depth=4)             # الرقبة
    s.ellipse((410, 405), 66, 82, 0.55, CLAY, depth=8, spec=0.6)         # الرأس (ينظر للأسفل)

    # --- الذراع الأمامية
    arm(0, 0, 40, 1.0, 0.55 * pulse)


def front_figure(s: Scene3D, flex: float = 0.0, glow: float = 0.6, highlight=True,
                 col=CLAY):
    """مانيكان أمامي. flex=1 يرفع الذراعين بوضعية استعراض العضلات."""
    mc = MUSCLE if highlight else col
    em = glow if highlight else 0.0
    # الساقان
    for sgn in (-1, 1):
        s.capsule((sgn * 52, 90), (sgn * 62, 330), 58, 42, col, depth=-10)
        s.capsule((sgn * 62, 330), (sgn * 64, 545), 40, 26, col, depth=-12)
    s.ellipse((0, 75), 100, 66, 0, col, depth=0)                          # الحوض
    s.ellipse((0, -40), 92, 118, 0, col, depth=6, spec=0.45, fibers=0)   # البطن
    s.ellipse((0, -165), 128, 100, 0, col, depth=10, spec=0.5)           # الصدر
    s.capsule((0, -250), (0, -290), 36, 36, col, depth=0)                # الرقبة
    s.ellipse((0, -335), 54, 68, 0, col, depth=14, spec=0.65)            # الرأس
    for sgn in (-1, 1):
        s.ellipse((sgn * 130, -195), 52, 48, 0, col, depth=16)           # الكتف
        if flex <= 0:
            el = (sgn * 158, -30)
            wr = (sgn * 172, 108)
            s.capsule((sgn * 138, -185), el, 42, 34, col, depth=4)
            s.capsule(el, wr, 37, 25, mc, depth=6, spec=0.55, emissive=em, fibers=12)
            s.ellipse((sgn * 174, 148), 27, 38, 0, col, depth=8)
        else:
            f = flex
            el = (sgn * (140 + 140 * f), -185 + 15 * f + 155 * (1 - f))
            wr = (sgn * (160 + 110 * f), -30 - 300 * f + 140 * (1 - f))
            s.capsule((sgn * 138, -185), el, 46, 38, col, depth=4)
            s.ellipse(((sgn * 138 + el[0]) / 2, (-185 + el[1]) / 2 - 18 * f), 46, 36 + 8 * f,
                      0, col, depth=12, spec=0.5)                         # البايسبس
            s.capsule(el, wr, 40, 27, mc, depth=10, spec=0.55, emissive=em, fibers=12)
            s.ellipse((wr[0], wr[1] - 30 * f), 36, 38, 0, col, depth=14)  # القبضة


def grip_panel(s: Scene3D, correct: bool, t: float):
    """لقطة قريبة: يد تمسك باراً أفقياً."""
    sway = math.sin(t * 2.2) * 4
    s.capsule((-60, 360), (560, 360), 30, 30, METAL, depth=0, spec=1.0)          # البار
    s.capsule((380, 360), (560, 360), 33, 33, METAL * 1.05, depth=1, spec=1.0)  # الكُم
    cx = 235 + sway
    s.capsule((cx, 1060), (cx, 640), 82, 62, CLAY, depth=10)                     # الساعد
    s.ellipse((cx, 520), 92, 120, 0, GRIP, depth=30, spec=0.5, emissive=0.10)    # الكف
    for i, dx in enumerate((-60, -20, 20, 60)):                                  # الأصابع
        top = 300 + abs(dx) * 0.25
        s.capsule((cx + dx * 1.05, 470), (cx + dx, top), 25, 22, GRIP, depth=62, spec=0.5,
                  emissive=0.08)
        s.ellipse((cx + dx, top + 8), 23, 20, 0, GRIP * 1.05, depth=70, spec=0.6,
                  emissive=0.08)
    if correct:
        # الإبهام يلتف تحت البار ويستقر فوق الأصابع
        s.capsule((cx - 90, 560), (cx - 85, 430), 30, 26, GRIP, depth=70, emissive=0.08)
        s.capsule((cx - 85, 430), (cx - 25, 398), 26, 22, GRIP, depth=96, spec=0.6,
                  emissive=0.08)
    else:
        # الإبهام بجانب السبابة فوق البار (قبضة بلا إبهام)
        s.capsule((cx - 88, 560), (cx - 118, 420), 30, 25, GRIP, depth=60, emissive=0.08)
        s.capsule((cx - 118, 420), (cx - 116, 318), 25, 22, GRIP, depth=80, spec=0.6,
                  emissive=0.08)


# ================================================================ رسوم إضافية (PIL)
def draw_x(img: Image.Image, cx, cy, r, alpha=1.0):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - r * 1.6, cy - r * 1.6, cx + r * 1.6, cy + r * 1.6], fill=(255, 40, 50, int(90 * alpha)))
    lay = lay.filter(ImageFilter.GaussianBlur(r * 0.45))
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(120, 10, 18, int(230 * alpha)),
              outline=(255, 70, 80, int(255 * alpha)), width=4)
    k = r * 0.45
    for a, b in (((cx - k, cy - k), (cx + k, cy + k)), ((cx - k, cy + k), (cx + k, cy - k))):
        d.line([a, b], fill=(255, 90, 100, int(255 * alpha)), width=max(5, int(r * 0.16)))
    img.alpha_composite(lay)


def draw_check(img: Image.Image, cx, cy, r, alpha=1.0, prog=1.0):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - r * 1.6, cy - r * 1.6, cx + r * 1.6, cy + r * 1.6], fill=(40, 255, 110, int(80 * alpha)))
    lay = lay.filter(ImageFilter.GaussianBlur(r * 0.45))
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(8, 90, 40, int(230 * alpha)),
              outline=(80, 255, 140, int(255 * alpha)), width=4)
    pts = [(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.35)]
    seg = [pts[0]]
    p = prog * 2
    seg.append(pts[1] if p >= 1 else (pts[0][0] + (pts[1][0] - pts[0][0]) * p,
                                      pts[0][1] + (pts[1][1] - pts[0][1]) * p))
    if p > 1:
        q = p - 1
        seg.append((pts[1][0] + (pts[2][0] - pts[1][0]) * q, pts[1][1] + (pts[2][1] - pts[1][1]) * q))
    d.line(seg, fill=(150, 255, 180, int(255 * alpha)), width=max(6, int(r * 0.17)), joint="curve")
    img.alpha_composite(lay)


def draw_arc_arrow(img: Image.Image, cx, cy, r, prog, col=(70, 255, 120)):
    """سهم دائري متوهج يوضح التفاف الإبهام."""
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    start, span = 110, 260 * prog
    if span < 5:
        return
    box = [cx - r, cy - r * 0.8, cx + r, cy + r * 0.8]
    d.arc(box, start, start + span, fill=col + (255,), width=14)
    end = math.radians(start + span)
    ex, ey = cx + r * math.cos(end), cy + r * 0.8 * math.sin(end)
    tang = end + math.pi / 2
    a1 = (ex + 34 * math.cos(tang), ey + 34 * math.sin(tang))
    a2 = (ex + 22 * math.cos(tang + 2.3), ey + 22 * math.sin(tang + 2.3))
    a3 = (ex + 22 * math.cos(tang - 2.3), ey + 22 * math.sin(tang - 2.3))
    d.polygon([a1, a2, a3], fill=col + (255,))
    glow = lay.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(glow)
    img.alpha_composite(glow)
    img.alpha_composite(lay)


@lru_cache(maxsize=1)
def muscle_strip() -> Image.Image:
    """شريط اختيار العضلة (3 مجسمات صغيرة، الوسط مُبرَز)."""
    tw, th = 120, 170
    strip = Image.new("RGBA", (tw * 3 + 80, th + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    d.rounded_rectangle([0, 0, strip.width - 1, strip.height - 1], 18, fill=(20, 21, 24, 190),
                        outline=(90, 92, 98, 200), width=2)
    for i in range(3):
        s = Scene3D(tw, th, 0.135, (tw / 2, th / 2 + 6))
        front_figure(s, 0, glow=0.5, highlight=(i == 1), col=CLAY * (0.75 if i == 1 else 0.45))
        im = s.shade(panel_bg(tw, th, (0.06, 0.06, 0.07)), glow=0.6 if i == 1 else 0)
        strip.paste(Image.fromarray(im), (20 + i * (tw + 20), 15))
    return strip


# ================================================================ تركيب الإطارات
LAY = {
    "main": (90, 380, 900, 1160),
    "left": (70, 470, 450, 980),
    "right": (560, 470, 450, 980),
}


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def wrist_angle(t):
    # دورة كاملة كل 2.6 ثانية: نزول بطيء ثم صعود
    ph = (t % 2.6) / 2.6
    v = ease(ph / 0.6) if ph < 0.6 else 1 - ease((ph - 0.6) / 0.4)
    return math.radians(-38 + 92 * v)          # -38° (أعلى) → 54° (أسفل)


def render_frame(args):
    gi, kind, lt, dur = args       # رقم الإطار، نوع المشهد، الزمن المحلي، مدة المشهد
    frame = Image.fromarray(frame_bg()).convert("RGBA")
    pulse = 0.75 + 0.25 * math.sin(lt * 5.0)
    intro = ease(lt / 0.45)

    if kind in ("hook", "exercise", "sets"):
        x, y, w, h = LAY["main"]
        if kind == "hook":            # زووم على الساعد
            z = 1.7 + 0.15 * lt / dur
            cam = (z, (450 - 600 * z, 560 - 680 * z))
        elif kind == "sets":
            z = 1.3
            cam = (z, (450 - 520 * z, 640 - 640 * z))
        else:
            z = 0.9 + 0.04 * lt / dur
            cam = (z, (450 - 420 * z, 680 - 715 * z))
        s = Scene3D(w, h, cam[0], cam[1])
        seated_figure(s, wrist_angle(lt + 0.6), pulse)
        img = s.shade(panel_bg(w, h), glow=1.0)
        yy = y + int((1 - intro) * 60)
        paste_panel(frame, img, x, yy, border_alpha=intro)
        if kind == "exercise":
            st = muscle_strip()
            frame.alpha_composite(st, (x + (w - st.width) // 2, yy + 30))
            # إطار برتقالي متوهج حول المجسم الأوسط
            lay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            bx = x + (w - st.width) // 2 + 20 + 140 - 8
            by = yy + 30 + 8
            ImageDraw.Draw(lay).rounded_rectangle([bx, by, bx + 136, by + 184], 14,
                                                  outline=(255, 140, 30, 255), width=6)
            g = lay.filter(ImageFilter.GaussianBlur(10))
            for _ in range(2):
                frame.alpha_composite(g)
            frame.alpha_composite(lay)
        if kind == "sets":
            # مؤشر الإيقاع: نزول (ثانيتان) / صعود
            ph = ((lt + 0.6) % 2.6) / 2.6
            down = ph < 0.6
            prog = ph / 0.6 if down else (ph - 0.6) / 0.4
            lay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            cx, cy, r = x + w - 120, yy + 120, 70
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 60), width=12)
            col = (255, 150, 40, 255) if down else (80, 255, 140, 255)
            d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * prog, fill=col, width=12)
            ar = 26
            if down:
                d.polygon([(cx - ar, cy - 10), (cx + ar, cy - 10), (cx, cy + ar)], fill=col)
            else:
                d.polygon([(cx - ar, cy + 10), (cx + ar, cy + 10), (cx, cy - ar)], fill=col)
            frame.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6)))
            frame.alpha_composite(lay)

    elif kind == "grip":
        for side, correct in (("left", False), ("right", True)):
            x, y, w, h = LAY[side]
            delay = 0.0 if side == "left" else 0.35
            k = ease((lt - delay) / 0.45)
            if k <= 0:
                continue
            s = Scene3D(w, h, 0.92, (10, 40))
            grip_panel(s, correct, lt)
            img = s.shade(panel_bg(w, h, (0.08, 0.11, 0.17), (0.5, 0.3)), glow=0.6)
            yy = y + int((1 - k) * 80)
            paste_panel(frame, img, x, yy, border_alpha=k)
            if correct:
                draw_arc_arrow(frame, x + 120, yy + 380, 78, ease((lt - 1.0) / 1.2))
                pop = ease((lt - 1.6) / 0.35)
                if pop > 0:
                    draw_check(frame, x + w - 85, yy + 110, int(46 * (0.6 + 0.4 * pop)), pop,
                               ease((lt - 1.7) / 0.5))
            else:
                pop = ease((lt - 0.8) / 0.35)
                if pop > 0:
                    shake = math.sin(lt * 40) * 6 * max(0, 1 - (lt - 0.8) / 0.6)
                    draw_x(frame, x + w - 85 + shake, yy + 110, int(46 * (0.6 + 0.4 * pop)), pop)

    elif kind == "cta":
        x, y, w, h = LAY["main"]
        flex = ease(lt / 0.9)
        s = Scene3D(w, h, 1.18, (w / 2, h / 2 + 160))
        front_figure(s, flex, glow=0.55 * pulse + 0.2)
        img = s.shade(panel_bg(w, h, (0.11, 0.10, 0.10), (0.5, 0.4)), glow=1.0)
        paste_panel(frame, img, x, y + int((1 - intro) * 60), glow_col=(255, 160, 70),
                    border_alpha=intro)

    draw_events(frame, gi / FPS)

    # وميض الانتقال
    if lt < 0.12 and gi > 0:
        a = int(140 * (1 - lt / 0.12))
        frame.alpha_composite(Image.new("RGBA", frame.size, (255, 255, 255, a)))
    return frame.convert("RGB").tobytes()


# ================================================================ الصوت
async def _tts(text, mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, config.VOICE, rate=config.VOICE_RATE, pitch=config.VOICE_PITCH)
    words = []
    with open(mp3, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"text": ch["text"], "start": ch["offset"] / 1e7,
                              "end": (ch["offset"] + ch["duration"]) / 1e7})
    return words


def probe(path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "default=nw=1:nk=1", str(path)],
                                capture_output=True, text=True, check=True).stdout.strip())


def make_voice(work: Path):
    out = []
    for i, sc in enumerate(SCENES):
        mp3 = work / f"v{i}.mp3"
        words = asyncio.run(_tts(sc["narration"], mp3))
        out.append({"file": mp3, "dur": probe(mp3), "words": words})
        print(f"  ✓ صوت المشهد {i + 1}: {out[-1]['dur']:.1f}s")
    return out


def synth_music(path: Path, total: float, cuts: list, sr=44100):
    """إيقاع رياضي بسيط مولَّد رياضياً + صوت 'ووش' عند كل انتقال."""
    n = int(total * sr)
    t = np.arange(n) / sr
    bpm = 118
    beat = 60 / bpm
    y = np.zeros(n)
    rng = np.random.default_rng(7)
    bass_notes = [55.0, 55.0, 65.41, 49.0]          # A1 A1 C2 G1
    for b in range(int(total / beat) + 1):
        st = int(b * beat * sr)
        if st >= n:
            break
        L = min(int(0.35 * sr), n - st)
        tt = np.arange(L) / sr
        # كيك
        f = 50 + 90 * np.exp(-tt * 30)
        y[st:st + L] += 0.9 * np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 9)
        # باص
        bf = bass_notes[(b // 4) % 4]
        Lb = min(int(beat * sr), n - st)
        tb = np.arange(Lb) / sr
        y[st:st + Lb] += 0.28 * np.tanh(3 * np.sin(2 * np.pi * bf * tb)) * np.exp(-tb * 3)
        # هاي هات على النصف
        hs = int((b + 0.5) * beat * sr)
        if hs < n:
            Lh = min(int(0.06 * sr), n - hs)
            noise = rng.standard_normal(Lh)
            noise = np.diff(np.concatenate([[0], noise]))          # high-pass بدائي
            y[hs:hs + Lh] += 0.10 * noise * np.exp(-np.arange(Lh) / sr * 60)
        # سنير على 2 و 4
        if b % 2 == 1:
            Ls = min(int(0.18 * sr), n - st)
            ts = np.arange(Ls) / sr
            y[st:st + Ls] += (0.22 * rng.standard_normal(Ls) + 0.2 * np.sin(2 * np.pi * 190 * ts)) \
                * np.exp(-ts * 22)
    # وسادة هارمونية خافتة
    for fr in (220.0, 261.63, 329.63):
        y += 0.025 * np.sin(2 * np.pi * fr * t) * (0.6 + 0.4 * np.sin(2 * np.pi * t / (beat * 8)))
    # ووش
    for c in cuts:
        st = int(max(c - 0.35, 0) * sr)
        L = min(int(0.5 * sr), n - st)
        if L <= 0:
            continue
        env = np.sin(np.linspace(0, np.pi, L)) ** 2
        noise = rng.standard_normal(L)
        k = np.linspace(0.02, 0.4, L)
        filt = np.zeros(L)
        acc = 0.0
        for i in range(L):                # low-pass متغير → صوت اندفاع
            acc += k[i] * (noise[i] - acc)
            filt[i] = acc
        y[st:st + L] += 0.5 * filt * env
    y *= np.minimum(1, np.minimum(t / 0.3, (total - t) / 1.2))
    y = np.tanh(y * 0.9) * 0.8
    st = np.stack([y, y], -1)
    pcm = (st * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


# ================================================================ النصوص (PIL + raqm)
# نرسم النص العربي داخل الإطار مباشرة (تشكيل HarfBuzz عبر raqm) بدل libass،
# لأن بعض نسخ ffmpeg تبني libass بدون HarfBuzz فتظهر الألف والياء مربعات.
GOLD = (255, 180, 48)
STYLES = {   # الحجم، اللون، سماكة الحد، المركز الافتراضي
    "Title": (96, (255, 255, 255), 6, (540, 205)),
    "Sub":   (62, GOLD, 5, (540, 318)),
    "Big":   (230, GOLD, 10, (540, 1330)),
    "Cap":   (70, (255, 255, 255), 6, (540, 1690)),
    "Lbl":   (52, (255, 255, 255), 5, (540, 960)),
    "Brand": (40, (255, 255, 255), 0, (540, 85)),
}
TIMELINE: list = []          # تُملأ في main وتُمرَّر للعمال


@lru_cache(maxsize=512)
def _font(size: int):
    from PIL import ImageFont, features
    if not features.check("raqm"):
        raise RuntimeError("Pillow بدون raqm: ثبّت libraqm0 libfribidi0 لتشكيل العربية")
    return ImageFont.truetype(str(config.FONTS / "Cairo-Bold.ttf"), size,
                              layout_engine=ImageFont.Layout.RAQM)


@lru_cache(maxsize=256)
def text_img(text: str, size: int, fill: tuple, stroke: int, alpha: int = 255) -> Image.Image:
    f = _font(size)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    x0, y0, x1, y1 = d0.textbbox((0, 0), text, font=f, stroke_width=stroke)
    pad = 24
    im = Image.new("RGBA", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad), (0, 0, 0, 0))
    if stroke:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - x0 + 4, pad - y0 + 6), text, font=f, fill=(0, 0, 0, 170),
                                stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(im).text((pad - x0, pad - y0), text, font=f, fill=fill + (alpha,),
                            stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    return im


def draw_events(frame: Image.Image, t: float):
    for ev in TIMELINE:
        if not (ev["start"] <= t < ev["end"]):
            continue
        lt, rem = t - ev["start"], ev["end"] - t
        size, col, stroke, pos = STYLES[ev["style"]]
        col = ev.get("color", col)
        pos = ev.get("pos", pos)
        fi, fo = ev.get("fade", (0.12, 0.12))
        a = min(1.0, lt / fi if fi else 1.0, rem / fo if fo else 1.0)
        anim = ev.get("anim", "fade")
        if anim == "pop":
            sc = 0.7 + 0.36 * ease(lt / 0.22) if lt < 0.22 else 1.06 - 0.06 * ease((lt - 0.22) / 0.1)
        elif anim == "big":
            sc = 0.4 + 0.7 * ease(lt / 0.26) if lt < 0.26 else 1.1 - 0.1 * ease((lt - 0.26) / 0.12)
        elif anim == "cap":
            sc = 0.92 + 0.08 * ease(lt / 0.12)
        else:
            sc = 1.0
        im = text_img(ev["text"], size, tuple(col), stroke, 102 if ev["style"] == "Brand" else 255)
        if abs(sc - 1) > 1e-3:
            im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
        if a < 1:
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * max(a, 0))))
        frame.alpha_composite(im, (int(pos[0] - im.width / 2), int(pos[1] - im.height / 2)))


def build_timeline(scenes: list, total: float) -> list:
    ev = [{"style": "Brand", "text": config.BRAND, "start": 0, "end": total, "fade": (0.3, 0.3)}]
    for sc in scenes:
        a, b = sc["start"], sc["start"] + sc["dur"]
        k = sc["kind"]
        if k == "sets":
            ev.append({"style": "Big", "text": sc["title"], "start": a + 0.2, "end": b, "anim": "big"})
            ev.append({"style": "Title", "text": sc["sub"], "start": a + 0.5, "end": b, "anim": "pop"})
        elif k == "grip":
            ev.append({"style": "Title", "text": sc["title"], "start": a, "end": b, "anim": "pop"})
            ly = LAY["left"][1] + LAY["left"][3] + 62
            ev.append({"style": "Lbl", "text": sc["left"], "start": a + 0.8, "end": b, "anim": "pop",
                       "pos": (LAY["left"][0] + LAY["left"][2] // 2, ly), "color": (255, 90, 90)})
            ev.append({"style": "Lbl", "text": sc["right"], "start": a + 1.6, "end": b, "anim": "pop",
                       "pos": (LAY["right"][0] + LAY["right"][2] // 2, ly), "color": (110, 255, 140)})
        else:
            ev.append({"style": "Title", "text": sc["title"], "start": a, "end": b, "anim": "pop"})
            if sc.get("sub"):
                ev.append({"style": "Sub", "text": sc["sub"], "start": a + 0.25, "end": b, "anim": "pop"})

        # الترجمة السفلية (التعليق الصوتي) — كلمة بكلمة إن توفرت التوقيتات
        words = sc.get("words") or []
        if not words:
            toks = sc["narration"].split()
            span = (sc.get("vdur") or sc["dur"] * 0.85) / max(len(toks), 1)
            words = [{"text": w, "start": i * span, "end": (i + 1) * span} for i, w in enumerate(toks)]
        groups, cur = [], []
        for w in words:
            if cur and (len(cur) >= 4 or len(" ".join(x["text"] for x in cur + [w])) > 24):
                groups.append(cur)
                cur = []
            cur.append(w)
        if cur:
            groups.append(cur)
        for gi, g in enumerate(groups):
            st = a + 0.15 + g[0]["start"]
            en = a + 0.15 + (groups[gi + 1][0]["start"] if gi + 1 < len(groups) else g[-1]["end"] + 0.3)
            en = min(en, b)
            if en > st:
                ev.append({"style": "Cap", "text": " ".join(x["text"] for x in g), "start": st,
                           "end": en, "anim": "cap", "fade": (0.06, 0.06)})
    return ev


def _init_worker(tl):
    global TIMELINE
    TIMELINE = tl


# ================================================================ التشغيل
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(config.OUT / "anim-forearm-short.mp4"))
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--preview", type=float, default=None, help="اعرض إطاراً واحداً عند الثانية X")
    args = ap.parse_args()

    work = config.OUT / "anim_work"
    work.mkdir(parents=True, exist_ok=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # 1) الصوت ← مدد المشاهد
    voices = None
    if not args.no_voice:
        try:
            voices = make_voice(work)
        except Exception as e:                               # noqa: BLE001
            print(f"  ! تعذّر التعليق الصوتي ({e}) — نكمل بالموسيقى والترجمة فقط")
            voices = None
    scenes, t = [], 0.0
    for i, sc in enumerate(SCENES):
        d = sc["min"]
        extra = {}
        if voices:
            d = max(d, voices[i]["dur"] + 0.45)
            extra = {"words": voices[i]["words"], "vdur": voices[i]["dur"]}
        scenes.append({**sc, **extra, "start": t, "dur": d})
        t += d
    if not voices or t < TARGET:                        # ضبط الإجمالي على 30 ثانية على الأقل
        f = TARGET / t
        t = 0.0
        for sc in scenes:
            sc["dur"] *= f
            sc["start"] = t
            t += sc["dur"]
    total = t
    print(f"• المدة: {total:.1f} ثانية")

    _init_worker(build_timeline(scenes, total))
    if args.preview is not None:
        for sc in scenes:
            if sc["start"] <= args.preview < sc["start"] + sc["dur"]:
                raw = render_frame((int(args.preview * FPS), sc["kind"], args.preview - sc["start"], sc["dur"]))
                p = work / f"preview_{args.preview:.1f}.png"
                Image.frombytes("RGB", (W, H), raw).save(p)
                print(p)
        return

    # 2) الإطارات
    jobs = []
    nframes = int(round(total * FPS))
    for gi in range(nframes):
        tt = gi / FPS
        sc = next((s for s in scenes if tt < s["start"] + s["dur"]), scenes[-1])
        jobs.append((gi, sc["kind"], tt - sc["start"], sc["dur"]))
    silent = work / "frames.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high",
                            "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    print(f"• رسم {nframes} إطاراً…")
    with Pool(args.workers, _init_worker, (TIMELINE,)) as pool:
        for i, raw in enumerate(pool.imap(render_frame, jobs, chunksize=4)):
            enc.stdin.write(raw)
            if i % 60 == 0:
                print(f"  {i}/{nframes}", flush=True)
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError("فشل ترميز الإطارات")

    # 3) الموسيقى + الترجمة + الصوت
    music = work / "music.wav"
    synth_music(music, total + 0.3, [s["start"] for s in scenes[1:]])

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(music)]
    if voices:
        for v in voices:
            cmd += ["-i", str(v["file"])]
        parts, labels = [], []
        for i, sc in enumerate(scenes):
            ms = int((sc["start"] + 0.15) * 1000)
            parts.append(f"[{i + 2}:a]aresample=44100,adelay={ms}|{ms},apad[v{i}]")
            labels.append(f"[v{i}]")
        fc = ";".join(parts) + ";" + "".join(labels) + \
            f"amix=inputs={len(voices)}:normalize=0:duration=longest,atrim=0:{total + 0.3:.2f},asplit=2[vo][sc];" \
            "[1:a]volume=-13dB[m];[m][sc]sidechaincompress=threshold=0.04:ratio=8:attack=10:release=300[md];" \
            "[vo][md]amix=inputs=2:normalize=0:duration=first[aout]"
    else:
        fc = "[1:a]volume=-4dB[aout]"
    cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-t", f"{total:.3f}",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-3000:])
        raise RuntimeError("فشل المونتاج النهائي")

    meta = {
        "title": "ساعد حديدي في 30 ثانية 💪 تمرين ثني الرسغ #shorts",
        "description": "تمرين ثني الرسغ (Wrist Curl) لساعد قوي وقبضة حديدية.\n"
                       "3 مجموعات × 15 تكراراً، مع نزول بطيء لمدة ثانيتين، ولُفّ الإبهام حول البار.\n\n"
                       f"موقعنا الرسمي: https://{config.SITE}",
        "tags": ["تمارين الساعد", "ثني الرسغ", "wrist curl", "قبضة قوية", "تمارين", "shorts"],
        "format": "shorts", "duration": round(total, 2), "video": out.name,
        "voice": bool(voices),
    }
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ جاهز: {out} ({out.stat().st_size / 1e6:.1f}MB, {total:.1f}s, صوت: {bool(voices)})")


if __name__ == "__main__":
    main()
