"""محرك فيديو تشريحي (v2): رسم رمادي + العضلات المستهدفة ملوّنة، بقوالب وثيمات مختلفة لكل قناة.

    python scripts/anatomy_video.py spec.json out.mp4

spec: format short|long, lang ar|en, title, subtitle, brand, site, scenes[].
أنواع المشاهد:
  pose  (افتراضي): pose, focus, hl[[muscle,"g"|"r"]], dots, arrows, label, icon ok|no, note, badge, stamp
  card : lines[], kind hook|myth|fact|vs|chapter|tip, icon
  split: left{pose,focus,hl,label}, right{...}, center "VS"
كل مشهد فيه say (نص التعليق الصوتي) يحدد مدته.
"""
import asyncio, json, math, os, shutil, subprocess, sys, time
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
IMG = Path(os.environ.get("ANATOMY_IMG", REPO / "assets" / "anatomy"))
FONTS = Path(os.environ.get("FONTS_DIR", REPO / "assets" / "fonts"))
FPS = 30
POSES = json.loads((IMG / "poses.json").read_text())
VOICES = {"ar": ("ar-EG-ShakirNeural", "+8%"), "en": ("en-US-AndrewNeural", "+5%")}

# ---------------- الثيمات: هوية مختلفة لكل قناة ----------------
THEMES = {
 "ar": dict(bg=(250, 250, 250), panel=(18, 18, 18), accent=(255, 210, 0), accent_txt=(0, 0, 0),
            ok=np.array([0.15, 0.74, 0.36]), ok_rgb=(40, 190, 90), no_rgb=(230, 60, 40),
            head=("Cairo-Black.ttf", 1.0), body=("Cairo-Bold.ttf", 1.0), rtl=True, upper=False),
 "en": dict(bg=(243, 246, 251), panel=(14, 26, 50), accent=(0, 196, 214), accent_txt=(10, 20, 40),
            ok=np.array([0.17, 0.50, 0.95]), ok_rgb=(45, 128, 240), no_rgb=(235, 70, 50),
            head=("Anton-Regular.ttf", 1.05), body=("Oswald-Bold.ttf", 0.95), rtl=False, upper=True),
}


def _dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                 "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True).stdout)


def speak(text, lang, out):
    """تعليق صوتي مجاني: edge-tts (صوت المصنع) مع إعادة المحاولة، ثم gTTS."""
    voice, rate = VOICES[lang]
    voice = os.environ.get("TTS_VOICE_EN" if lang == "en" else "TTS_VOICE", voice)
    for attempt in range(6):
        try:
            import edge_tts
            asyncio.run(asyncio.wait_for(edge_tts.Communicate(text, voice, rate=rate).save(str(out)), timeout=45))
            if Path(out).stat().st_size > 1000:
                return _dur(out)
        except Exception as e:                       # noqa: BLE001
            print(f"  ! edge-tts ({voice}, {attempt + 1}):", str(e)[:80])
        time.sleep(4 * (attempt + 1))
    from gtts import gTTS
    gTTS(text=text, lang=lang).save(str(out))
    return _dur(out)


# ---------------- الرسومات والعضلات ----------------
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
    lo, hi = (np.percentile(lum[red], 3), np.percentile(lum[red], 97)) if red.any() else (0, 1)
    shade = np.where(red, np.clip((lum - lo) / (hi - lo + 1e-6), 0, 1), np.clip(lum * 1.2, 0, 1))
    base_red = src[red].mean(0) if red.any() else np.array([0.95, 0.3, 0.18])
    seeds = POSES[name]
    names = list(seeds); pts = [(n, p) for n in names for p in seeds[n]]
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.stack([(xx - p[0]) ** 2 + (yy - p[1]) ** 2 for _, p in pts])
    near = dist.argmin(0)
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
            py, px = np.nonzero((near == first) & redm)
            if len(px) > 50:
                c = np.array([px.mean(), py.mean()])
                ev, evec = np.linalg.eigh(np.cov(np.stack([px - c[0], py - c[1]])))
                v = evec[:, -1]; L = 1.5 * math.sqrt(ev[-1])
                axis[n] = (tuple(c - v * L), tuple(c + v * L))
    ys, xs = np.nonzero(lum < 0.86)
    person = (np.percentile(xs, .2), np.percentile(ys, .2), np.percentile(xs, 99.8), np.percentile(ys, 99.8))
    return dict(gray=gray, shade=shade, masks=masks, bbox=bbox, axis=axis, W=W, H=H, person=person, base_red=base_red)


def tint(base, shade, mask, color, a):
    col = color[None, None, :] * (0.55 + 0.62 * shade[..., None])
    m = (mask * a)[..., None]
    return base * (1 - m) + np.clip(col, 0, 1) * m


def viewport(P, focus, aspect):
    W, H = P["W"], P["H"]
    if not focus or focus == "full":
        x0, y0, x1, y1 = P["person"]; pad = 1.08
    else:
        fl = focus if isinstance(focus, list) else [focus]
        bbs = [P["bbox"][m] for m in fl if m in P["bbox"]] or [P["person"]]
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


def crop(img, box, size, bg):
    W, H = img.size
    x0, y0, x1, y1 = box
    sc = size[0] / (x1 - x0)
    out = Image.new("RGB", size, bg)
    ix0, iy0, ix1, iy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if ix1 <= ix0 or iy1 <= iy0: return out
    part = img.crop((int(ix0), int(iy0), int(ix1), int(iy1)))
    pw, ph = max(1, round((ix1 - ix0) * sc)), max(1, round((iy1 - iy0) * sc))
    part = part.resize((pw, ph), Image.LANCZOS)
    # الخلفية البيضاء للرسم → لون الثيم
    a = np.asarray(part).astype(np.float32)
    wmask = (a.min(-1) > 238)[..., None]
    a = np.where(wmask, np.array(bg, np.float32), a)
    out.paste(Image.fromarray(a.astype(np.uint8)), (round((ix0 - x0) * sc), round((iy0 - y0) * sc)))
    return out


def ease(t): return 1 - (1 - t) ** 3


# ---------------- رسم العناصر ----------------
class Ctx:
    def __init__(self, lang, fmt):
        self.T = THEMES[lang]; self.lang = lang; self.fmt = fmt; self.rtl = self.T["rtl"]

    def font(self, kind, size):
        f, k = self.T[kind]
        return ImageFont.truetype(str(FONTS / f), int(size * k))

    def kw(self, s):
        return dict(direction="rtl", language="ar") if self.rtl and not s.isascii() else {}

    def tx(self, s):
        return s.upper() if self.T["upper"] else s

    def w(self, d, s, f): return d.textlength(s, font=f, **self.kw(s))

    def text(self, d, x, y, s, f, fill, align="c", stroke=0, sfill=(0, 0, 0)):
        s = self.tx(s); w = self.w(d, s, f)
        x0 = x - w / 2 if align == "c" else (x - w if align == "r" else x)
        d.text((x0, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill, **self.kw(s))
        return w

    def wrap(self, d, s, f, maxw):
        s = self.tx(s); lines, cur = [], ""
        for wd in s.split():
            t = (cur + " " + wd).strip()
            if self.w(d, t, f) <= maxw or not cur: cur = t
            else: lines.append(cur); cur = wd
        if cur: lines.append(cur)
        return lines

    def fit(self, d, s, kind, size, maxw, minsize=28):
        while size > minsize and self.w(d, self.tx(s), self.font(kind, size)) > maxw: size -= 2
        return self.font(kind, size)


def icon(d, cx, cy, rr, kind, C):
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=C.T["ok_rgb"] if kind == "ok" else C.T["no_rgb"], outline=(255, 255, 255), width=max(3, int(rr * .14)))
    k = rr * .5; wd = max(3, int(rr * .28))
    if kind == "ok":
        d.line([(cx - k, cy), (cx - k * .2, cy + k * .8), (cx + k, cy - k * .7)], fill="white", width=wd, joint="curve")
    else:
        d.line([(cx - k, cy - k), (cx + k, cy + k)], fill="white", width=wd)
        d.line([(cx - k, cy + k), (cx + k, cy - k)], fill="white", width=wd)


def arrow(d, tip, direction, s, col):
    x, y = tip; sg = 1 if direction == "right" else -1
    pts = [(x, y), (x - sg * s, y - s * .7), (x - sg * s, y - s * .3), (x - sg * s * 2.1, y - s * .3),
           (x - sg * s * 2.1, y + s * .3), (x - sg * s, y + s * .3), (x - sg * s, y + s * .7)]
    d.polygon(pts, fill=col, outline=(0, 0, 0))


def dots(d, p1, p2, col, r):
    d.line([p1, p2], fill=(255, 255, 255), width=max(4, int(r * .4)))
    for p in (p1, p2):
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=(255, 255, 255))
        d.ellipse((p[0] - r * .63, p[1] - r * .63, p[0] + r * .63, p[1] + r * .63), fill=col)
        d.ellipse((p[0] - r * .26, p[1] - r * .26, p[0] + r * .26, p[1] + r * .26), fill=(255, 255, 255))


@lru_cache(maxsize=64)
def _layer(name, hl_key, lang, intro):
    """صورة الرسم ملوّنة بالكامل (تُحسب مرة لكل مشهد)."""
    P = pose(name); T = THEMES[lang]
    img = P["gray"]
    if intro:
        img = tint(img, P["shade"], np.clip(sum(P["masks"].values()), 0, 1), P["base_red"], .95)
    for m, c in hl_key:
        if m in P["masks"]:
            img = tint(img, P["shade"], P["masks"][m], T["ok"] if c == "g" else P["base_red"], 1.0)
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def pose_view(C, sub, t, dur, size, start_box):
    """يرسم منطقة الرسم لمشهد pose (أو نصف مشهد split)."""
    P = pose(sub["pose"])
    aspect = size[0] / size[1]
    v = viewport(P, sub.get("focus"), aspect)
    sb = start_box or viewport(P, "full", aspect)
    k = ease(min(1, t / .35))
    a = [sb[j] + (v[j] - sb[j]) * k for j in range(4)]
    push = 1 - .05 * (t / max(dur, .1))
    cx, cy = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
    hw, hh = (a[2] - a[0]) / 2 * push, (a[3] - a[1]) / 2 * push
    box = (cx - hw, cy - hh, cx + hw, cy + hh)
    hl = sub.get("hl", [])
    key = tuple((m, c) for m, c in hl)
    base = crop(_layer(sub["pose"], (), C.lang, False), box, size, C.T["bg"])
    if sub.get("all_red_intro"):
        a_ = max(0., 1 - t / 1.4)
        if a_ > 0: base = Image.blend(base, crop(_layer(sub["pose"], (), C.lang, True), box, size, C.T["bg"]), a_)
    if key:
        alpha = min(1, t / .25) * (.93 + .07 * math.sin(t * 7))
        view = Image.blend(base, crop(_layer(sub["pose"], key, C.lang, False), box, size, C.T["bg"]), alpha)
    else:
        view = base
    d0 = ImageDraw.Draw(view)
    sc_ = size[0] / (box[2] - box[0])                  # بكسل شاشة لكل بكسل صورة
    to = lambda p: ((p[0] - box[0]) * sc_, (p[1] - box[1]) * sc_)   # noqa: E731
    if t > .35 and hl:
        col = C.T["ok_rgb"] if hl[0][1] == "g" else C.T["no_rgb"]
        m0 = hl[0][0]
        if sub.get("dots") and m0 in P["axis"]:
            dots(d0, to(P["axis"][m0][0]), to(P["axis"][m0][1]), col, 20)
        if sub.get("arrows") and m0 in P["bbox"]:
            b = P["bbox"][m0]; my = (b[1] + b[3]) / 2; off = 10 * math.sin(t * 10)
            l, r = to((b[0], my)), to((b[2], my))
            arrow(d0, (l[0] - 12 + off, l[1]), "right", 34, C.T["accent"])
            arrow(d0, (r[0] + 12 - off, r[1]), "left", 34, C.T["accent"])
    return view, v


def stamp(fr, C, text, kind, cx, cy, size):
    """ختم «خرافة/حقيقة» مائل."""
    f = C.font("head", size)
    lay = Image.new("RGBA", fr.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    col = C.T["ok_rgb"] if kind == "ok" else C.T["no_rgb"]
    s = C.tx(text); w = C.w(d, s, f); h = size * 1.35
    d.rounded_rectangle((cx - w / 2 - 40, cy - h / 2, cx + w / 2 + 40, cy + h / 2), radius=18, outline=col + (255,), width=10, fill=(255, 255, 255, 215))
    d.text((cx - w / 2, cy - h / 2 + size * .05), s, font=f, fill=col + (255,), **C.kw(s))
    lay = lay.rotate(-8 if C.rtl else 8, center=(cx, cy), resample=Image.BICUBIC)
    fr.paste(lay, (0, 0), lay)


# ---------------- التخطيطات ----------------
def layout(C):
    if C.fmt == "short":
        W, H = 1080, 1920
        if C.lang == "ar": area = (0, 230, 1080, 1560)
        else: area = (0, 330, 1080, 1160)
    else:
        W, H = 1920, 1080
        area = (760, 0, 1160, 1080) if C.lang == "ar" else (0, 0, 1180, 1080)
    return W, H, area


def draw_chrome(fr, d, C, spec, sc, t, prog):
    """العناوين والتسميات حسب الثيم والتنسيق."""
    T = C.T; W, H = fr.size
    if C.fmt == "short" and C.lang == "ar":
        d.rectangle((0, 0, W, 230), fill=T["panel"])
        C.text(d, W / 2, 18, spec["title"], C.fit(d, spec["title"], "head", 92, W - 80), T["accent"])
        C.text(d, W / 2, 138, spec.get("subtitle", ""), C.fit(d, spec.get("subtitle", ""), "body", 50, W - 80), (255, 255, 255))
        d.rectangle((0, 222, W * prog, 230), fill=T["accent"])
        y = 1570
        if sc.get("label") and t > .2:
            f = C.fit(d, sc["label"], "head", 64, W - 220, 40)
            y += pill(d, C, W / 2, y, sc["label"], f, (20, 20, 20), (255, 255, 255), sc.get("icon")) + 16
        if sc.get("note") and t > .9:
            f = C.fit(d, sc["note"], "body", 42, W - 160, 30)
            pill(d, C, W / 2, y, sc["note"], f, T["ok_rgb"] if sc.get("note_ok", True) else T["no_rgb"], (255, 255, 255))
        C.text(d, W - 40, H - 62, spec["brand"], C.font("body", 30), (120, 120, 120), "r")
    elif C.fmt == "short":                       # ZMAFIT: عنوان في صندوق أعلى اليسار، تسمية أسفل اليسار
        f = C.fit(d, spec["title"], "head", 110, W - 160, 60)
        tw = C.w(d, C.tx(spec["title"]), f)
        d.rectangle((40, 60, 40 + tw + 60, 60 + f.size * 1.35), fill=T["panel"])
        d.rectangle((40, 60, 52, 60 + f.size * 1.35), fill=T["accent"])
        C.text(d, 80, 60 + f.size * .1, spec["title"], f, (255, 255, 255), "l")
        fs = C.fit(d, spec.get("subtitle", ""), "body", 46, W - 120, 28)
        sw = C.w(d, C.tx(spec.get("subtitle", "")), fs)
        d.rectangle((40, 60 + f.size * 1.35, 40 + sw + 50, 60 + f.size * 1.35 + fs.size * 1.6), fill=T["accent"])
        C.text(d, 65, 60 + f.size * 1.35 + fs.size * .2, spec.get("subtitle", ""), fs, T["accent_txt"], "l")
        y = 1520
        if sc.get("label") and t > .2:
            f2 = C.fit(d, sc["label"], "head", 84, W - 220, 46)
            lines = [C.tx(sc["label"])]
            lw = C.w(d, lines[0], f2)
            d.rectangle((40, y, 40 + lw + 140, y + f2.size * 1.4), fill=T["panel"])
            if sc.get("icon"): icon(d, 40 + 60, y + f2.size * .7, f2.size * .42, sc["icon"], C)
            C.text(d, 40 + (115 if sc.get("icon") else 30), y + f2.size * .12, sc["label"], f2, (255, 255, 255), "l")
            y += f2.size * 1.4 + 14
        if sc.get("note") and t > .9:
            f3 = C.fit(d, sc["note"], "body", 46, W - 160, 28)
            nw = C.w(d, C.tx(sc["note"]), f3)
            d.rectangle((40, y, 40 + nw + 50, y + f3.size * 1.6), fill=T["accent"] if sc.get("note_ok", True) else T["no_rgb"])
            C.text(d, 65, y + f3.size * .2, sc["note"], f3, T["accent_txt"], "l")
        d.rectangle((0, H - 14, W * prog, H), fill=T["accent"])
        C.text(d, W - 40, H - 70, spec["brand"], C.font("head", 34), T["panel"], "r")
    else:                                        # long
        ar = C.lang == "ar"
        aw = 1160 if ar else 1180
        px0 = 0 if ar else aw; pw = W - aw
        d.rectangle((px0, 0, px0 + pw, H), fill=T["panel"])
        d.rectangle((px0 + (pw - 10 if ar else 0), 0, px0 + (pw if ar else 10), H), fill=T["accent"])
        xr = px0 + pw - 60 if ar else px0 + 60; al = "r" if ar else "l"
        C.text(d, xr, 50, spec["title"], C.fit(d, spec["title"], "head", 70, pw - 120, 40), T["accent"], al)
        C.text(d, xr, 150, spec.get("subtitle", ""), C.fit(d, spec.get("subtitle", ""), "body", 38, pw - 120, 24), (210, 210, 210), al)
        if sc.get("chapter"):
            C.text(d, xr, 255, sc["chapter"], C.fit(d, sc["chapter"], "body", 38, pw - 120, 24), (150, 150, 150), al)
        y = 340
        if sc.get("label") and t > .2:
            f = C.font("head", 60)
            if sc.get("icon"): icon(d, xr - 28 if ar else xr + 28, y + 46, 30, sc["icon"], C)
            for ln in C.wrap(d, sc["label"], f, pw - 200):
                C.text(d, xr - (75 if ar and sc.get("icon") else 0) + (0 if ar else (75 if sc.get("icon") else 0)), y, ln, f, (255, 255, 255), al)
                y += 92
        if sc.get("note") and t > .9:
            y += 20; f = C.font("body", 40)
            for ln in C.wrap(d, sc["note"], f, pw - 140):
                C.text(d, xr, y, ln, f, (130, 230, 150) if sc.get("note_ok", True) and ar else (T["accent"] if sc.get("note_ok", True) else (255, 120, 110)), al)
                y += 62
        d.rectangle((px0 + 60, H - 40, px0 + 60 + (pw - 120) * prog, H - 30), fill=T["accent"])
        C.text(d, xr, H - 110, spec["brand"], C.font("body", 32), (140, 140, 140), al)
    if sc.get("cta") and t > .3:
        if C.fmt == "short":
            bx, by = W / 2, 1720 if C.lang == "ar" else 1760
        else:
            bx, by = ((0 if C.lang == "ar" else 1180) + (W - (1160 if C.lang == "ar" else 1180)) / 2), 820
        maxw = (W - 160) if C.fmt == "short" else (W - 1180 - 120)
        f = C.fit(d, sc["cta"], "body", 48, maxw - 80, 26)
        pill(d, C, bx, by, sc["cta"], f, T["accent"], T["accent_txt"])
        if spec.get("site"): C.text(d, bx, by + f.size + 60, spec["site"], C.font("body", 32), (150, 150, 150))


def pill(d, C, x, y, s, f, bg, fg, ic=None):
    s = C.tx(s); tw = C.w(d, s, f); h = f.size + 36
    iw = h if ic else 0; w = tw + 70 + iw
    x0 = x - w / 2
    d.rounded_rectangle((x0, y, x0 + w, y + h), radius=h / 2, fill=bg)
    d.text((x0 + 35 + (0 if C.rtl else iw), y + 6), s, font=f, fill=fg, **C.kw(s))
    if ic:
        cx = x0 + w - 35 - iw * .4 if C.rtl else x0 + 35 + iw * .25
        icon(d, cx, y + h / 2, iw * .36, ic, C)
    return h


def card_frame(C, spec, sc, t, size):
    """بطاقة نصية كاملة (خطاف، خرافة، حقيقة، VS، فصل)."""
    T = C.T; W, H = size
    fr = Image.new("RGB", size, T["panel"]); d = ImageDraw.Draw(fr)
    kind = sc.get("kind", "hook")
    k = ease(min(1, t / .3))
    col = {"myth": T["no_rgb"], "fact": T["ok_rgb"]}.get(kind, T["accent"])
    d.rectangle((0, 0, W, 16 + 8 * k), fill=col); d.rectangle((0, H - 16 - 8 * k, W, H), fill=col)
    lines = sc.get("lines", [])
    big = 120 if C.fmt == "short" else 100
    maxw = W - 140
    blocks = []
    for i, ln in enumerate(lines):
        if not ln: continue
        size = big if i == 0 else int(big * .55)
        while True:
            f = C.font("head" if i == 0 else "body", size)
            wl = C.wrap(d, ln, f, maxw)
            if (len(wl) <= 3 and all(C.w(d, x, f) <= maxw for x in wl)) or size < 40: break
            size -= 6
        for x in wl:
            blocks.append((x, f, col if i == 0 else (255, 255, 255)))
    tot = sum(f.size * 1.35 for _, f, _ in blocks) + (big * 1.6 if sc.get("icon") else 0)
    y = (H - tot) / 2 + (1 - k) * 60
    if sc.get("icon"):
        icon(d, W / 2, y + big * .6, big * .55, sc["icon"], C); y += big * 1.6
    for wl, f, c in blocks:
        C.text(d, W / 2, y, wl, f, c); y += f.size * 1.35
    return fr


def render(spec, out_path, workdir=None):
    fmt = spec.get("format", "short"); lang = spec.get("lang", "ar")
    C = Ctx(lang, fmt)
    W, H, (ax, ay, aw, ah) = layout(C)
    wd = Path(workdir or (REPO / "work_anat")); shutil.rmtree(wd, ignore_errors=True); wd.mkdir(parents=True)
    scenes = spec["scenes"]; voice = []
    for i, sc in enumerate(scenes):
        sc.setdefault("dur", 2.0)
        if sc.get("say") and not os.environ.get("NO_VOICE"):
            mp3 = wd / f"v_{i:02d}.mp3"
            sc["dur"] = max(sc["dur"] if not sc.get("say") else 1.4, speak(sc["say"], lang, mp3) + .35)
            voice.append((i, mp3))
    total = sum(s["dur"] for s in scenes); nft = int(round(total * FPS))
    frame = 0; t0 = 0.; starts = []; prev = {}
    for sc in scenes:
        starts.append(t0)
        kind = sc.get("type", "pose")
        n = int(round(sc["dur"] * FPS))
        for i in range(n):
            t = i / FPS; prog = (frame + 1) / nft
            if kind == "card":
                fr = card_frame(C, spec, sc, t, (W, H))
            else:
                fr = Image.new("RGB", (W, H), C.T["bg"])
                if kind == "split":
                    vert = ah > aw                      # عمودي: فوق/تحت
                    sw, sh = (aw, ah // 2 - 4) if vert else (aw // 2 - 6, ah)
                    for j, side in enumerate(("left", "right")):
                        view, _ = pose_view(C, sc[side], t, sc["dur"], (sw, sh), None)
                        fr.paste(view, (ax, ay + j * (sh + 8)) if vert else (ax + j * (sw + 12), ay))
                    d = ImageDraw.Draw(fr)
                    if vert:
                        d.rectangle((ax, ay + sh, ax + aw, ay + sh + 8), fill=C.T["panel"]); cx_, cy_ = ax + aw / 2, ay + sh + 4
                    else:
                        d.rectangle((ax + sw, ay, ax + sw + 12, ay + ah), fill=C.T["panel"]); cx_, cy_ = ax + sw + 6, ay + ah * .45
                    vs = sc.get("center", "VS"); f = C.font("head", 90); r_ = 85
                    d.ellipse((cx_ - r_, cy_ - r_, cx_ + r_, cy_ + r_), fill=C.T["accent"], outline=C.T["panel"], width=8)
                    C.text(d, cx_, cy_ - f.size * .62, vs, f, C.T["accent_txt"])
                    for j, side in enumerate(("left", "right")):
                        lab = sc[side].get("label")
                        if lab:
                            ff = C.fit(d, lab, "head", 64, sw - 80, 30)
                            lx = ax + (aw / 2 if vert else j * (sw + 12) + sw / 2)
                            ly = (ay + j * (sh + 8) + sh - ff.size * 1.8) if vert else (ay + ah - ff.size * 2.2)
                            lw = C.w(d, C.tx(lab), ff)
                            bb = d.textbbox((lx - lw / 2, ly), C.tx(lab), font=ff, **C.kw(lab))
                            d.rounded_rectangle((bb[0] - 24, bb[1] - 14, bb[2] + 24, bb[3] + 14), radius=14, fill=C.T["panel"])
                            C.text(d, lx, ly, lab, ff, (255, 255, 255))
                else:
                    key = sc["pose"]
                    sb = prev.get("box") if prev.get("pose") == key else None
                    view, vb = pose_view(C, sc, t, sc["dur"], (aw, ah), sb)
                    fr.paste(view, (ax, ay))
                d = ImageDraw.Draw(fr)
                draw_chrome(fr, d, C, spec, sc, t, prog)
                if sc.get("badge") and t > .15:
                    f = C.font("head", 80); bx = ax + (aw - 120 if C.rtl else aw - 130); by = ay + (150 if C.lang == "ar" else 470)
                    d.ellipse((bx - 80, by - 80, bx + 80, by + 80), fill=C.T["accent"], outline=C.T["panel"], width=8)
                    C.text(d, bx, by - f.size * .62, sc["badge"], f, C.T["accent_txt"])
                if sc.get("stamp") and t > .25:
                    stamp(fr, C, sc["stamp"], sc.get("icon", "no"), ax + aw / 2, ay + ah * .22, 96 if C.fmt == "short" else 80)
            fr.save(wd / f"f_{frame:05d}.jpg", quality=90)
            frame += 1
        if kind == "pose":
            P = pose(sc["pose"]); prev = {"pose": sc["pose"], "box": viewport(P, sc.get("focus"), aw / ah)}
        else:
            prev = {}
        t0 += sc["dur"]

    inputs = ["-f", "lavfi", "-i", f"anoisesrc=d={total}:c=pink:a=0.0001"]; filt, parts = [], []; idx = 2
    for i, mp3 in voice:
        inputs += ["-i", str(mp3)]; ms = int((starts[i] + .15) * 1000)
        filt.append(f"[{idx}]aresample=44100,volume=1.6,adelay={ms}|{ms}[a{idx}]"); parts.append(f"[a{idx}]"); idx += 1
    for ct, sc in zip(starts, scenes):
        inputs += ["-f", "lavfi", "-i", "anoisesrc=d=0.35:c=white:a=0.5"]; ms = int(ct * 1000)
        filt.append(f"[{idx}]highpass=f=800,lowpass=f=5000,afade=t=in:d=0.12,afade=t=out:st=0.15:d=0.2,volume=0.22,adelay={ms}|{ms}[a{idx}]")
        parts.append(f"[a{idx}]"); idx += 1
        if sc.get("icon"):
            inputs += ["-f", "lavfi", "-i", f"sine=f={'880' if sc['icon'] == 'ok' else '160'}:d=0.25"]; ms = int((ct + .3) * 1000)
            filt.append(f"[{idx}]afade=t=out:st=0.1:d=0.15,volume={'0.18' if sc['icon'] == 'ok' else '0.28'},adelay={ms}|{ms}[a{idx}]")
            parts.append(f"[a{idx}]"); idx += 1
    fc = ";".join(filt) + f";[1]{''.join(parts)}amix=inputs={len(parts) + 1}:normalize=0:duration=first,aformat=channel_layouts=stereo[aout]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", str(wd / "f_%05d.jpg"), *inputs,
                    "-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", f"{total:.2f}", str(out_path)], check=True)
    return out_path


def debug_maps(out_dir, names=None):
    pal = [(46, 204, 113), (52, 152, 219), (241, 196, 15), (231, 76, 60), (155, 89, 182), (26, 188, 156), (230, 126, 34)]
    Path(out_dir).mkdir(exist_ok=True, parents=True)
    for name in names or POSES:
        P = pose(name); img = P["gray"].copy()
        for i, (m, mk) in enumerate(P["masks"].items()):
            img = tint(img, P["shade"], mk, np.array(pal[i % len(pal)]) / 255, .9)
        pil = Image.fromarray((img * 255).astype(np.uint8)); d = ImageDraw.Draw(pil)
        f = ImageFont.truetype(str(FONTS / "Cairo-Bold.ttf"), max(24, pil.size[0] // 30))
        for m, b in P["bbox"].items():
            d.text(((b[0] + b[2]) / 2 - 30, (b[1] + b[3]) / 2), m, font=f, fill=(0, 0, 0))
        pil.thumbnail((800, 800)); pil.save(Path(out_dir) / f"dbg_{name}.jpg")


if __name__ == "__main__":
    if sys.argv[1] == "debug":
        debug_maps(sys.argv[2], sys.argv[3].split(",") if len(sys.argv) > 3 else None)
    else:
        render(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), sys.argv[2])
