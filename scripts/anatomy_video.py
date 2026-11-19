"""محرك فيديو تشريحي: رسم رمادي + العضلة المستهدفة بالأخضر (صحيح) أو الأحمر (خطأ).

الاستخدام:
    python anatomy_video.py spec.json out.mp4
spec.json يصف الفيديو (short/long، اللغة، المشاهد). يكتبه Gemini تلقائياً في المصنع.
"""
import json, math, subprocess, sys, shutil
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import os, asyncio
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
IMG = Path(os.environ.get("ANATOMY_IMG", REPO / "assets" / "anatomy"))
FONTS = Path(os.environ.get("FONTS_DIR", REPO / "assets" / "fonts"))
VOICES = {"ar": ("ar-EG-ShakirNeural", "+8%"), "en": ("en-US-AndrewNeural", "+5%")}


def _dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                 "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True).stdout)


def speak(text, lang, out):
    """تعليق صوتي مجاني: edge-tts (نفس صوت المصنع) ثم gTTS احتياطاً."""
    voice, rate = VOICES[lang]
    voice = os.environ.get("TTS_VOICE", voice)
    try:
        import edge_tts
        asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(out)))
        if Path(out).stat().st_size > 1000:
            return _dur(out)
    except Exception as e:                       # noqa: BLE001
        print("  ! edge-tts:", e)
    from gtts import gTTS
    gTTS(text=text, lang=lang).save(str(out))
    return _dur(out)
FPS = 30

# نقاط مرجعية لكل عضلة في كل رسم (إحداثيات الصورة الأصلية)
POSES = {
 "front": {"chest": [(440, 440), (680, 445)], "delts": [(300, 410), (815, 385)], "biceps": [(300, 570), (790, 570)],
           "abs": [(560, 620), (560, 760)], "quads": [(400, 1220), (700, 1210)], "calves": [(360, 1560), (680, 1570)]},
 "back": {"traps": [(560, 330)], "delts": [(300, 420), (830, 420)], "triceps": [(290, 580), (860, 580)],
          "lats": [(430, 620), (700, 620)], "glutes": [(470, 960), (650, 960)],
          "hamstrings": [(440, 1240), (700, 1240)], "calves": [(410, 1590), (720, 1590)]},
 "side": {"chest": [(500, 470)], "delts": [(640, 400)], "triceps": [(690, 570)], "abs": [(560, 680)],
          "glutes": [(720, 950)], "quads": [(560, 1250)], "calves": [(650, 1580)]},
 "biceps": {"delts": [(380, 300), (780, 300)], "biceps": [(250, 350), (900, 350)], "chest": [(500, 420), (690, 420)],
            "abs": [(590, 640)], "quads": [(420, 1150), (740, 1150)]},
 "squat": {"abs": [(660, 640)], "chest": [(780, 560)], "quads": [(430, 870), (850, 860)], "calves": [(470, 1080), (880, 1070)]},
 "pushup": {"delts": [(1470, 320)], "chest": [(1650, 430)], "triceps": [(1420, 560), (1730, 580)], "abs": [(1240, 500)]},
}

GREEN = np.array([0.15, 0.74, 0.36]); RED = np.array([0.95, 0.30, 0.18])
YEL = (255, 210, 0); OKC = (40, 200, 70); NOC = (235, 40, 35)


@lru_cache(maxsize=None)
def pose(name):
    src = np.asarray(Image.open(IMG / f"{name}.jpg").convert("RGB")).astype(np.float32) / 255
    H, W = src.shape[:2]
    r, g, b = src[..., 0], src[..., 1], src[..., 2]
    mx, mn = src.max(-1), src.min(-1)
    sat = (mx - mn) / (mx + 1e-6)
    lum = 0.30 * r + 0.59 * g + 0.11 * b
    red = (r > g * 1.3) & (r > b * 1.3) & (sat > 0.30)
    soft = (r > g * 1.06) & (r > b * 1.06) & (sat > 0.10)
    soft = np.asarray(Image.fromarray((soft * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
                      .filter(ImageFilter.GaussianBlur(2))) / 255.0
    g1 = np.clip(lum * 1.55 + 0.12, 0, 1)[..., None].repeat(3, -1)
    gray = src * (1 - soft[..., None]) + np.where(red[..., None], g1, lum[..., None].repeat(3, -1)) * soft[..., None]
    lo, hi = np.percentile(lum[red], 3), np.percentile(lum[red], 97)
    shade = np.where(red, np.clip((lum - lo) / (hi - lo + 1e-6), 0, 1), np.clip(lum * 1.2, 0, 1))
    base_red = src[red].mean(0)                               # نفس أحمر الرسم الأصلي
    # تقسيم الأحمر حسب أقرب نقطة مرجعية
    seeds = POSES[name]
    names = list(seeds); pts = [(n, p) for n in names for p in seeds[n]]
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.stack([(xx - p[0]) ** 2 + (yy - p[1]) ** 2 for _, p in pts])
    near = dist.argmin(0)                                   # أقرب نقطة مرجعية (لكل جهة)
    owner = np.array([names.index(n) for n, _ in pts])[near]
    redm = np.asarray(Image.fromarray((red * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
    masks, bbox, axis = {}, {}, {}
    for i, n in enumerate(names):
        hard = (owner == i) & redm
        masks[n] = np.asarray(Image.fromarray(hard.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(1.5))) / 255.0
        ys, xs = np.nonzero(hard)
        if len(xs):
            bbox[n] = (xs.min(), ys.min(), xs.max(), ys.max())
            first = [j for j, (nn, _) in enumerate(pts) if nn == n][0]
            py, px = np.nonzero((near == first) & redm)          # جهة واحدة فقط
            if len(px) > 50:
                c = np.array([px.mean(), py.mean()])
                cov = np.cov(np.stack([px - c[0], py - c[1]]))
                ev, evec = np.linalg.eigh(cov)
                v = evec[:, -1]; L = 1.5 * math.sqrt(ev[-1])
                axis[n] = (tuple(c - v * L), tuple(c + v * L))
    ys, xs = np.nonzero(lum < 0.86)                           # حدود الشخص (بدون الخلفية البيضاء)
    person = (np.percentile(xs, 0.2), np.percentile(ys, 0.2), np.percentile(xs, 99.8), np.percentile(ys, 99.8))
    return dict(base_red=base_red, person=person, src=src, gray=gray, shade=shade, masks=masks, bbox=bbox, axis=axis, W=W, H=H)


def tint(base, shade, mask, color, a):
    col = color[None, None, :] * (0.55 + 0.62 * shade[..., None])
    m = (mask * a)[..., None]
    return base * (1 - m) + np.clip(col, 0, 1) * m


def F(size, w="Black"):
    return ImageFont.truetype(str(FONTS / f"Cairo-{w}.ttf"), size)


class Canvas:
    def __init__(self, fmt, rtl):
        self.fmt, self.rtl = fmt, rtl
        if fmt == "short":
            self.W, self.H = 1080, 1920
            self.area = (0, 230, 1080, 1560)        # x, y, w, h لمنطقة الرسم
        else:
            self.W, self.H = 1920, 1080
            self.area = (760, 0, 1160, 1080) if rtl else (0, 0, 1160, 1080)

    def kw(self, s):
        return dict(direction="rtl", language="ar") if self.rtl and not s.isascii() else {}

    def text(self, d, x, y, s, font, fill, align="c", stroke=0):
        w = d.textlength(s, font=font, **self.kw(s))
        x0 = x - w / 2 if align == "c" else (x - w if align == "r" else x)
        d.text((x0, y), s, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0), **self.kw(s))
        return w

    def wrap(self, d, s, font, maxw):
        words, lines, cur = s.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font, **self.kw(t)) <= maxw or not cur:
                cur = t
            else:
                lines.append(cur); cur = w
        if cur: lines.append(cur)
        return lines

    def pill(self, d, x, y, s, font, bg, fg, icon=None, align="c", maxw=None):
        tw = d.textlength(s, font=font, **self.kw(s)); h = font.size + 36
        iw = h if icon else 0; w = tw + 70 + iw
        x0 = x - w / 2 if align == "c" else (x - w if align == "r" else x)
        d.rounded_rectangle((x0, y, x0 + w, y + h), radius=h / 2, fill=bg)
        d.text((x0 + 35 + (0 if self.rtl else iw), y + 6), s, font=font, fill=fg, **self.kw(s))
        if icon:
            cx = x0 + w - 35 - iw * 0.4 if self.rtl else x0 + 35 + iw * 0.25
            icon_draw(d, cx, y + h / 2, iw * 0.36, icon)
        return h


def icon_draw(d, cx, cy, rr, kind):
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=OKC if kind == "ok" else NOC, outline=(255, 255, 255), width=5)
    k = rr * 0.5; wdt = max(3, int(rr * 0.28))
    if kind == "ok":
        d.line([(cx - k, cy), (cx - k * 0.2, cy + k * 0.8), (cx + k, cy - k * 0.7)], fill="white", width=wdt, joint="curve")
    else:
        d.line([(cx - k, cy - k), (cx + k, cy + k)], fill="white", width=wdt)
        d.line([(cx - k, cy + k), (cx + k, cy - k)], fill="white", width=wdt)


def arrow(d, tip, direction, s, col=YEL):
    x, y = tip; sg = 1 if direction == "right" else -1
    pts = [(x, y), (x - sg * s, y - s * .7), (x - sg * s, y - s * .3), (x - sg * s * 2.1, y - s * .3),
           (x - sg * s * 2.1, y + s * .3), (x - sg * s, y + s * .3), (x - sg * s, y + s * .7)]
    d.polygon(pts, fill=col, outline=(0, 0, 0))


def dots(d, p1, p2, col, r):
    d.line([p1, p2], fill=(255, 255, 255), width=max(4, int(r * 0.4)))
    for p in (p1, p2):
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=(255, 255, 255))
        d.ellipse((p[0] - r * .63, p[1] - r * .63, p[0] + r * .63, p[1] + r * .63), fill=col)
        d.ellipse((p[0] - r * .26, p[1] - r * .26, p[0] + r * .26, p[1] + r * .26), fill=(255, 255, 255))


def ease(t): return 1 - (1 - t) ** 3


def viewport(P, sc, aspect):
    """نافذة التكبير: كل الجسم أو العضلات المطلوبة مع هامش."""
    W, H = P["W"], P["H"]
    focus = sc.get("focus")
    if not focus or focus == "full":
        x0, y0, x1, y1 = P["person"]
        pad = 1.08
    else:
        bbs = [P["bbox"][m] for m in (focus if isinstance(focus, list) else [focus]) if m in P["bbox"]]
        x0 = min(b[0] for b in bbs); y0 = min(b[1] for b in bbs); x1 = max(b[2] for b in bbs); y1 = max(b[3] for b in bbs)
        pad = 1.7
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) * pad, (y1 - y0) * pad
    if w / h < aspect: w = h * aspect
    else: h = w / aspect
    if focus and focus != "full":
        mh = max(H, W) * 0.34
        if h < mh: h = mh; w = h * aspect
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def crop(arr_img, box, size):
    """قص مع حشو أبيض إن خرجت النافذة عن الصورة."""
    W, H = arr_img.size
    x0, y0, x1, y1 = box
    sc = size[0] / (x1 - x0)
    out = Image.new("RGB", size, (250, 250, 250))
    ix0, iy0, ix1, iy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if ix1 <= ix0 or iy1 <= iy0: return out
    part = arr_img.crop((int(ix0), int(iy0), int(ix1), int(iy1)))
    pw, ph = max(1, round((ix1 - ix0) * sc)), max(1, round((iy1 - iy0) * sc))
    out.paste(part.resize((pw, ph), Image.LANCZOS), (round((ix0 - x0) * sc), round((iy0 - y0) * sc)))
    return out


def render(spec, out_path, workdir=None):
    fmt = spec.get("format", "short"); lang = spec.get("lang", "ar"); rtl = lang == "ar"
    C = Canvas(fmt, rtl)
    ax, ay, aw, ah = C.area
    aspect = aw / ah
    wd = Path(workdir or (ROOT / "work")); shutil.rmtree(wd, ignore_errors=True); wd.mkdir(parents=True)
    scenes = spec["scenes"]
    voice_parts = []
    for i, sc in enumerate(scenes):
        if sc.get("say") and not os.environ.get("NO_VOICE"):
            mp3 = wd / f"v_{i:02d}.mp3"
            d_ = speak(sc["say"], lang, mp3)
            sc["dur"] = max(sc.get("dur", 1.5), d_ + 0.35)
            voice_parts.append((i, mp3))
    total = sum(s["dur"] for s in scenes)
    nframes_total = int(round(total * FPS))
    frame = 0; prev = None; prev_pose = None; cuts = []
    t0 = 0.0
    for sc in scenes:
        P = pose(sc["pose"])
        v = viewport(P, sc, aspect)
        start_v = prev if (prev is not None and prev_pose == sc["pose"]) else viewport(P, {"focus": "full"}, aspect)
        if prev_pose != sc["pose"] and (sc.get("focus") in (None, "full")):
            start_v = (v[0] + (v[2] - v[0]) * .06, v[1] + (v[3] - v[1]) * .06, v[2] - (v[2] - v[0]) * .06, v[3] - (v[3] - v[1]) * .06)
        cuts.append((t0, sc))
        n = int(round(sc["dur"] * FPS))
        hl = sc.get("hl", [])
        for i in range(n):
            t = i / FPS
            k = ease(min(1, t / 0.35))
            a = [start_v[j] + (v[j] - start_v[j]) * k for j in range(4)]
            push = 1 - 0.05 * (t / sc["dur"])
            cx, cy = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
            hw, hh = (a[2] - a[0]) / 2 * push, (a[3] - a[1]) / 2 * push
            box = (cx - hw, cy - hh, cx + hw, cy + hh)
            img = P["gray"]
            if sc.get("all_red_intro"):
                allm = np.clip(sum(P["masks"].values()), 0, 1)
                img = tint(img, P["shade"], allm, RED, max(0.0, 1 - t / 1.4) * .95)
            pulse = .93 + .07 * math.sin(t * 7)
            for m, c in hl:
                if m in P["masks"]:
                    img = tint(img, P["shade"], P["masks"][m], GREEN if c == "g" else P["base_red"], min(1, t / .25) * pulse)
            pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
            d0 = ImageDraw.Draw(pil)
            scale_ref = (box[2] - box[0]) / aw          # بكسل الصورة لكل بكسل شاشة
            if t > .35 and hl:
                col = OKC if hl[0][1] == "g" else NOC
                if sc.get("dots") and hl[0][0] in P["axis"]:
                    p1, p2 = P["axis"][hl[0][0]]
                    dots(d0, p1, p2, col, 20 * scale_ref)
                if sc.get("arrows") and hl[0][0] in P["bbox"]:
                    b = P["bbox"][hl[0][0]]; my = (b[1] + b[3]) / 2; off = 10 * scale_ref * math.sin(t * 10)
                    s = 34 * scale_ref
                    arrow(d0, (b[0] - 12 * scale_ref + off, my), "right", s)
                    arrow(d0, (b[2] + 12 * scale_ref - off, my), "left", s)
            view = crop(pil, box, (aw, ah))
            fr = Image.new("RGB", (C.W, C.H), (250, 250, 250))
            fr.paste(view, (ax, ay))
            d = ImageDraw.Draw(fr)
            prog = (frame + 1) / nframes_total
            if fmt == "short":
                d.rectangle((0, 0, C.W, ay), fill=(18, 18, 18))
                C.text(d, C.W / 2, 18, spec["title"], F(92), YEL)
                C.text(d, C.W / 2, 138, spec.get("subtitle", ""), F(50, "Bold"), (255, 255, 255))
                d.rectangle((0, ay - 8, C.W * prog, ay), fill=YEL)
                y = 1560
                if sc.get("label") and t > .2:
                    y += C.pill(d, C.W / 2, y, sc["label"], F(64 if len(sc["label"]) < 26 else 52), (20, 20, 20), (255, 255, 255), sc.get("icon")) + 16
                if sc.get("note") and t > .9:
                    C.pill(d, C.W / 2, y, sc["note"], F(42, "Bold"), OKC if sc.get("note_ok", True) else NOC, (255, 255, 255))
                d.text((C.W - 30 - d.textlength(spec["brand"], font=F(30, "Bold")) if rtl else 30, C.H - 64), spec["brand"],
                       font=F(30, "Bold"), fill=(120, 120, 120))
            else:   # long: لوحة نص جانبية
                px0 = 0 if rtl else aw
                pw = C.W - aw
                d.rectangle((px0, 0, px0 + pw, C.H), fill=(18, 18, 18))
                d.rectangle((px0 + (pw - 10 if rtl else 0), 0, px0 + (pw if rtl else 10), C.H), fill=YEL)
                xr = px0 + pw - 60 if rtl else px0 + 60
                al = "r" if rtl else "l"
                C.text(d, xr, 50, spec["title"], F(70), YEL, al)
                C.text(d, xr, 150, spec.get("subtitle", ""), F(38, "Bold"), (210, 210, 210), al)
                if sc.get("chapter"):
                    C.text(d, xr, 260, sc["chapter"], F(40, "Bold"), (150, 150, 150), al)
                y = 340
                if sc.get("label") and t > .2:
                    for ln in C.wrap(d, sc["label"], F(62), pw - 170):
                        C.text(d, xr - (70 if rtl and sc.get("icon") else 0) + (0 if rtl else (70 if sc.get("icon") else 0)), y, ln, F(62), (255, 255, 255), al)
                        y += 92
                    if sc.get("icon"):
                        icon_draw(d, xr - 28 if rtl else xr + 28, 340 + 50, 30, sc["icon"])
                if sc.get("note") and t > .9:
                    y += 20
                    for ln in C.wrap(d, sc["note"], F(42, "Bold"), pw - 140):
                        C.text(d, xr, y, ln, F(42, "Bold"), (120, 230, 140) if sc.get("note_ok", True) else (255, 120, 110), al)
                        y += 66
                d.rectangle((px0 + 60, C.H - 40, px0 + 60 + (pw - 120) * prog, C.H - 30), fill=YEL)
                C.text(d, xr, C.H - 110, spec["brand"], F(32, "Bold"), (140, 140, 140), al)
            if sc.get("cta") and t > .3:
                bx = C.W / 2 if fmt == "short" else (px0 + pw / 2)
                by = 1700 if fmt == "short" else 760
                C.pill(d, bx, by, sc["cta"], F(48, "Bold"), YEL, (0, 0, 0))
                if spec.get("site"):
                    C.text(d, bx, by + 110, spec["site"], F(34, "Bold"), (150, 150, 150))
            fr.save(wd / f"f_{frame:05d}.jpg", quality=90)
            frame += 1
        prev, prev_pose = v, sc["pose"]
        t0 += sc["dur"]

    # صوت: موسيقى/صوت معلّق اختياري + ووش عند القطع + نغمة صح/خطأ
    inputs, filt, parts = [], [], []
    inputs += ["-f", "lavfi", "-i", f"anoisesrc=d={total}:c=pink:a=0.0001"]
    idx = 2
    starts = [c[0] for c in cuts]
    for i, mp3 in voice_parts:
        inputs += ["-i", str(mp3)]
        ms = int((starts[i] + 0.15) * 1000)
        filt.append(f"[{idx}]aresample=44100,volume=1.6,adelay={ms}|{ms}[a{idx}]"); parts.append(f"[a{idx}]"); idx += 1
    music = spec.get("music")
    if music and Path(music).exists():
        inputs += ["-stream_loop", "-1", "-i", music]
        filt.append(f"[{idx}]volume=0.10,atrim=0:{total:.2f}[a{idx}]"); parts.append(f"[a{idx}]"); idx += 1
    for ct, sc in cuts:
        inputs += ["-f", "lavfi", "-i", "anoisesrc=d=0.35:c=white:a=0.5"]
        ms = int(ct * 1000)
        filt.append(f"[{idx}]highpass=f=800,lowpass=f=5000,afade=t=in:d=0.12,afade=t=out:st=0.15:d=0.2,volume=0.22,adelay={ms}|{ms}[a{idx}]")
        parts.append(f"[a{idx}]"); idx += 1
        if sc.get("icon"):
            inputs += ["-f", "lavfi", "-i", f"sine=f={'880' if sc['icon']=='ok' else '160'}:d=0.25"]
            ms = int((ct + .3) * 1000)
            filt.append(f"[{idx}]afade=t=out:st=0.1:d=0.15,volume={'0.18' if sc['icon']=='ok' else '0.28'},adelay={ms}|{ms}[a{idx}]")
            parts.append(f"[a{idx}]"); idx += 1
    fc = ";".join(filt) + f";[1]{''.join(parts)}amix=inputs={len(parts)+1}:normalize=0:duration=first,aformat=channel_layouts=stereo[aout]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", str(wd / "f_%05d.jpg"), *inputs,
                    "-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", f"{total:.2f}", str(out_path)], check=True)
    return out_path


def debug_maps(out_dir):
    pal = [(46, 204, 113), (52, 152, 219), (241, 196, 15), (231, 76, 60), (155, 89, 182), (26, 188, 156), (230, 126, 34)]
    for name in POSES:
        P = pose(name); img = P["gray"].copy()
        for i, (m, mk) in enumerate(P["masks"].items()):
            img = tint(img, P["shade"], mk, np.array(pal[i % len(pal)]) / 255, .9)
        pil = Image.fromarray((img * 255).astype(np.uint8)); d = ImageDraw.Draw(pil)
        for m, b in P["bbox"].items():
            d.text(((b[0] + b[2]) / 2 - 30, (b[1] + b[3]) / 2), m, font=F(36, "Bold"), fill=(0, 0, 0))
        for m, (p1, p2) in P["axis"].items():
            dots(d, p1, p2, (0, 0, 0), 12)
        pil.thumbnail((700, 700)); pil.save(Path(out_dir) / f"dbg_{name}.jpg")


if __name__ == "__main__":
    if sys.argv[1] == "debug":
        debug_maps(sys.argv[2])
    else:
        render(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), sys.argv[2])
