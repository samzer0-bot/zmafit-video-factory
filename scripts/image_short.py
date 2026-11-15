"""شورتس 30 ثانية من رسمة تشريحية جاهزة (مجسّم بعضلة مُلوَّنة بالأحمر).

الكاميرا تتحرك داخل الرسمة (زووم/تحريك)، العضلة المستهدفة تنبض وتتوهج،
مع عناوين وترجمة عربية، وموسيقى، وتعليق صوتي (edge-tts) إن توفر.

    python scripts/image_short.py                       # تمرين البايسبس الافتراضي
    python scripts/image_short.py --no-voice --workers 4
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anim_short as A  # noqa: E402  (نعيد استعمال النصوص والموسيقى والصوت والرسوم)
import config            # noqa: E402

W, H, FPS = A.W, A.H, A.FPS
PAD = 500                                   # هامش أبيض حول الرسمة لتحريك الكاميرا بحرية
PANEL = (90, 380, 900, 1160)
SIDE_L = (70, 470, 450, 980)
SIDE_R = (560, 470, 450, 980)

EXERCISE = {
    "image": "assets/figures/biceps_curl.png",
    "meta_title": "بايسبس ضخم في 30 ثانية 💪 تمرين الكيرل بالدمبل #shorts",
    "meta_desc": "تمرين الكيرل بالدمبل (Dumbbell Curl) لتضخيم العضلة ذات الرأسين.\n"
                 "ثبّت المرفقين، ارفع وأنت تعصر العضلة، وانزل ببطء. 3 مجموعات × 12 تكراراً.",
    "tags": ["تمارين البايسبس", "كيرل دمبل", "dumbbell curl", "biceps", "تضخيم الذراع", "shorts"],
    # مراكز الكاميرا في إحداثيات الرسمة الأصلية (x, y, ارتفاع الإطار)
    "cam": {
        "full": (616, 650, 1300),
        "muscle_a": (366, 634, 430),          # البايسبس الأيسر (الذراع الممدودة)
        "muscle_b": (850, 690, 860),          # الذراع المثنية مع الدمبل (تتسع للنزول)
        "arm_a": (300, 820, 980),
        "arm_b": (880, 640, 980),
    },
    "label": "العضلة ذات الرأسين",
    "label_at": (366, 634),
    "scenes": [
        {"kind": "hook", "min": 3.6, "title": "بايسبس ضخم", "sub": "في 30 ثانية فقط",
         "narration": "تريد بايسبس ضخمًا؟ هذا أفضل تمرين له!"},
        {"kind": "anatomy", "min": 6.5, "title": "الكيرل بالدمبل", "sub": "DUMBBELL CURL",
         "narration": "تمرين الكيرل بالدمبل يستهدف العضلة ذات الرأسين في الذراع مباشرة."},
        {"kind": "steps", "min": 8.0, "title": "طريقة الأداء", "sub": None,
         "steps": ["1  ثبّت المرفقين بجانبك", "2  ارفع واعصر العضلة", "3  انزل ببطء"],
         "narration": "ثبّت مرفقيك بجانب جسمك، ارفع الدمبل وأنت تعصر العضلة، ثم انزل ببطء."},
        {"kind": "form", "min": 7.0, "title": "انتبه للأداء", "left": "لا تؤرجح جسمك",
         "right": "المرفق ثابت",
         "narration": "لا تؤرجح جسمك لرفع الوزن، بل اجعل المرفق ثابتًا طوال الحركة."},
        {"kind": "cta", "min": 4.9, "title": "3 × 12", "sub": "تابعنا للمزيد",
         "narration": "نفّذ ثلاث مجموعات من اثنتي عشرة عدة، وتابعنا للمزيد!"},
    ],
}


# ------------------------------------------------------------------ الرسمة والقناع
@lru_cache(maxsize=1)
def source():
    im = Image.open(config.ROOT / EXERCISE["image"]).convert("RGB")
    a = np.asarray(im).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = ((r > 150) & (r - g > 32) & (r - b > 36)).astype(np.uint8) * 255   # يشمل لمعة العضلة
    mask = (Image.fromarray(m).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(7))
            .filter(ImageFilter.GaussianBlur(1.2)))           # إغلاق الثقوب داخل العضلة
    big = Image.new("RGB", (im.width + 2 * PAD, im.height + 2 * PAD), (255, 255, 255))
    big.paste(im, (PAD, PAD))
    bm = Image.new("L", big.size, 0)
    bm.paste(mask, (PAD, PAD))
    return big, bm


# ------------------------------------------------------------------ تحريك الذراع
# الساعد مع الدمبل يدور حول المرفق، والبايسبس ينتفخ عند الانقباض.
ARM = {
    "pivot": (836, 776),                       # مركز مفصل المرفق
    "joint_r": 50,                             # قرص المفصل (يدور على نفسه بلا فراغات)
    "forearm": [(838, 676), (866, 640), (862, 440), (1220, 420), (1220, 712), (1005, 712),
                (905, 800), (862, 845), (836, 826), (824, 742), (832, 712)],
    "muscle_anchor": (772, 640),               # نقطة ثبات البايسبس عند التضخيم
    "max_angle": 80.0,                         # زاوية النزول القصوى
    "rep": 2.6,                                # ثوانٍ لكل تكرار
}


def rep_pose(t: float):
    """(الزاوية، الانتفاخ): نزول بطيء ثم صعود سريع مع عصر في الأعلى."""
    ph = (t % ARM["rep"]) / ARM["rep"]
    if ph < 0.12:
        k = 0.0                                # ثبات وعصر في الأعلى
    elif ph < 0.62:
        k = ease((ph - 0.12) / 0.5)            # نزول بطيء
    else:
        k = 1 - ease((ph - 0.62) / 0.38)       # صعود
    return ARM["max_angle"] * k, 1.0 + 0.09 * (1 - k)


@lru_cache(maxsize=1)
def _arm_parts():
    big, bm = source()
    px, py = ARM["pivot"][0] + PAD, ARM["pivot"][1] + PAD
    poly = Image.new("L", big.size, 0)
    ImageDraw.Draw(poly).polygon([(x + PAD, y + PAD) for x, y in ARM["forearm"]], fill=255)
    jr = ARM["joint_r"]
    disc = Image.new("L", big.size, 0)
    ImageDraw.Draw(disc).ellipse([px - jr, py - jr, px + jr, py + jr], fill=255)
    erase_m = Image.fromarray(np.minimum(np.asarray(poly), 255 - np.asarray(disc)))
    poly = Image.fromarray(np.maximum(np.asarray(poly), np.asarray(disc)))
    # لون البايسبس يبقى مكانه (لا يُسحب مع الساعد)
    red = 255 - np.asarray(bm.point(lambda v: 255 if v > 20 else 0).filter(ImageFilter.MaxFilter(5)))
    poly = Image.fromarray(np.minimum(np.asarray(poly), red))
    erase_m = Image.fromarray(np.minimum(np.asarray(erase_m), red))
    poly = poly.filter(ImageFilter.GaussianBlur(1.5))
    erase_m = erase_m.filter(ImageFilter.GaussianBlur(1.5))
    R = 560
    box = (px - R, py - R, px + R, py + R)
    piece = big.crop(box).convert("RGBA")
    piece.putalpha(poly.crop(box))
    erased = big.copy()
    erased.paste((255, 255, 255), mask=erase_m)
    # البايسبس: قصاصة بحواف ناعمة حول المنطقة الحمراء
    mb = bm.point(lambda v: 255 if v > 20 else 0)
    ax = ARM["muscle_anchor"][0] + PAD
    mb_r = Image.new("L", big.size, 0)
    mb_r.paste(mb.crop((ax - 40, 0, big.width, big.height)), (ax - 40, 0))
    mb_r = mb_r.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(3))
    bb = mb_r.getbbox()
    mus = big.crop(bb).convert("RGBA")
    mus.putalpha(mb_r.crop(bb))
    mus_m = bm.crop(bb)
    return erased, bm, piece, box, mus, mus_m, bb


def animated_source(t: float):
    ang, bulge = rep_pose(t)
    erased, bm, piece, box, mus, mus_m, bb = _arm_parts()
    img = erased.copy()
    m = bm.copy()
    if bulge > 1.001:
        ax, ay = ARM["muscle_anchor"][0] + PAD, ARM["muscle_anchor"][1] + PAD
        w, h = mus.size
        nw, nh = int(w * bulge), int(h * (1 + (bulge - 1) * 0.5))
        sm = mus.resize((nw, nh), Image.BICUBIC)
        smm = mus_m.resize((nw, nh), Image.BILINEAR)
        nx = int(ax - (ax - bb[0]) * bulge)
        ny = int(ay - (ay - bb[1]) * (1 + (bulge - 1) * 0.5))
        img.paste(sm, (nx, ny), sm)
        m.paste(smm, (nx, ny), sm.getchannel("A"))
    rp = piece.rotate(-ang, resample=Image.BICUBIC, center=(piece.width / 2, piece.height / 2))
    img.paste(rp, (box[0], box[1]), rp)
    # الساعد يغطي ما تحته من القناع
    m.paste(0, (box[0], box[1]), rp.getchannel("A"))
    return img, m


def lerp(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


def cam_view(cam, w, h, rot=0.0, t=None):
    """يقص منطقة من الرسمة (مركز وارتفاع) ويعيدها بمقاس اللوحة مع قناع العضلة.
    t: إن أُعطي، تتحرك الذراع المثنية (تكرار كيرل)."""
    big, bm = source() if t is None else animated_source(t)
    cx, cy, ch = cam
    cw = ch * w / h
    x0, y0 = cx - cw / 2 + PAD, cy - ch / 2 + PAD
    if rot:
        # دوران حول أسفل الإطار (يحاكي تأرجح الجسم)
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        px, py = cx + PAD, cy + PAD + ch * 0.45
        sx, sy = cw / w, ch / h
        # تحويل أفيني: إحداثيات الإخراج → المصدر
        a = c * sx
        b = s * sy
        d = -s * sx
        e = c * sy
        ox, oy = x0 - px, y0 - py
        cc = px + c * ox + s * oy
        ff = py - s * ox + c * oy
        coef = (a, b, cc, d, e, ff)
        img = big.transform((w, h), Image.AFFINE, coef, Image.BICUBIC, fillcolor=(255, 255, 255))
        msk = bm.transform((w, h), Image.AFFINE, coef, Image.BILINEAR)
    else:
        box = (x0, y0, x0 + cw, y0 + ch)
        img = big.transform((w, h), Image.EXTENT, box, Image.BICUBIC)
        msk = bm.transform((w, h), Image.EXTENT, box, Image.BILINEAR)
    return img, msk


def pulse_muscle(img: Image.Image, msk: Image.Image, t: float, amount=1.0) -> np.ndarray:
    """العضلة تنبض: لون أحمر ← برتقالي متوهج + هالة حولها."""
    p = 0.5 + 0.5 * math.sin(t * 5.2)
    a = np.asarray(img).astype(np.float32) / 255
    m = (np.asarray(msk).astype(np.float32) / 255)[..., None] * amount
    hot = np.array([1.0, 0.55 + 0.25 * p, 0.12], np.float32)
    lit = a * (0.75 + 0.5 * p) + hot * 0.35 * (0.4 + 0.6 * p)
    out = a * (1 - m) + np.clip(lit, 0, 1) * m
    # هالة خارجية
    halo = msk.filter(ImageFilter.GaussianBlur(14))
    hm = (np.asarray(halo).astype(np.float32) / 255)[..., None] * (1 - m) * amount * (0.35 + 0.45 * p)
    out = out * (1 - hm * 0.6) + np.array([1.0, 0.35, 0.08], np.float32) * hm * 0.6
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def ease(x):
    return A.ease(x)


# ------------------------------------------------------------------ الإطارات
def render_frame(job):
    gi, kind, lt, dur = job
    cams = EXERCISE["cam"]
    frame = Image.fromarray(A.frame_bg()).convert("RGBA")
    intro = ease(lt / 0.45)
    x, y, w, h = PANEL

    if kind in ("hook", "anatomy", "steps", "cta"):
        if kind == "hook":
            cam = lerp(cams["muscle_a"], (cams["muscle_a"][0], cams["muscle_a"][1], 520), ease(lt / dur))
        elif kind == "anatomy":
            k = ease((lt - 0.2) / 1.6)
            cam = lerp(cams["muscle_a"][:2] + (600,), cams["full"], k)
            cam = (cam[0], cam[1], cam[2] * (1 - 0.04 * lt / dur))
        elif kind == "steps":
            cam = lerp(cams["full"], cams["muscle_b"], ease((lt - 0.3) / 1.8))
        else:
            cam = (cams["full"][0], cams["full"][1], cams["full"][2] * (1 - 0.08 * lt / dur))
        img, msk = cam_view(cam, w, h, t=None if kind == "hook" else gi / FPS)
        arr = pulse_muscle(img, msk, lt)
        yy = y + int((1 - intro) * 60)
        A.paste_panel(frame, arr, x, yy, glow_col=(255, 150, 70) if kind == "cta" else (200, 200, 205),
                      border_alpha=intro)

        if kind == "anatomy" and lt > 1.9:
            # خط إشارة من العضلة إلى اسمها
            k = ease((lt - 1.9) / 0.5)
            lx, ly = EXERCISE["label_at"]
            sx = x + (lx - cam[0]) * h / cam[2] + w / 2
            sy = yy + (ly - cam[1]) * h / cam[2] + h / 2
            tx, ty = x + 120, yy + 230
            lay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            ex, ey = sx + (tx - sx) * k, sy + (ty - sy) * k
            d.line([(sx, sy), (ex, ey)], fill=(255, 120, 30, 255), width=6)
            d.ellipse([sx - 14, sy - 14, sx + 14, sy + 14], outline=(255, 120, 30, 255), width=6)
            frame.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6)))
            frame.alpha_composite(lay)
            if k >= 1:
                ti = A.text_img(EXERCISE["label"], 50, (255, 255, 255), 5)
                bx, by = int(tx + 10), int(ty - ti.height - 8)
                pill = Image.new("RGBA", frame.size, (0, 0, 0, 0))
                ImageDraw.Draw(pill).rounded_rectangle(
                    [bx + 8, by + 18, bx + ti.width - 8, by + ti.height - 10], 18, fill=(225, 70, 20, 235))
                frame.alpha_composite(pill)
                frame.alpha_composite(ti, (bx, by))

        if kind == "steps":
            # خطوات الأداء تظهر تباعاً على شريط داكن أسفل اللوحة
            steps = EXERCISE["scenes"][2]["steps"]
            seg = (dur - 1.4) / len(steps)
            for i, s in enumerate(steps):
                st = 1.2 + i * seg
                if lt < st:
                    continue
                k = ease((lt - st) / 0.3)
                active = lt < st + seg or i == len(steps) - 1
                col = (255, 180, 48) if active else (235, 235, 235)
                ti = A.text_img(s, 54, col, 5)
                by = yy + h - 330 + i * 100
                bar = Image.new("RGBA", frame.size, (0, 0, 0, 0))
                ImageDraw.Draw(bar).rounded_rectangle(
                    [x + 60, by - 8, x + w - 60, by + 82], 24, fill=(15, 15, 18, int(215 * k)))
                frame.alpha_composite(bar)
                ti = ti.copy()
                ti.putalpha(ti.getchannel("A").point(lambda v: int(v * k)))
                frame.alpha_composite(ti, (int(x + w / 2 - ti.width / 2 + (1 - k) * 60), by - 20))

    elif kind == "form":
        for side, ok in (("L", False), ("R", True)):
            px, py, pw, ph = SIDE_L if side == "L" else SIDE_R
            delay = 0.0 if side == "L" else 0.35
            k = ease((lt - delay) / 0.45)
            if k <= 0:
                continue
            if ok:
                img, msk = cam_view(cams["arm_b"], pw, ph, t=gi / FPS)
            else:
                rot = 7 * math.sin(lt * 4.2)            # تأرجح خاطئ
                img, msk = cam_view(cams["arm_a"], pw, ph, rot=rot)
            arr = pulse_muscle(img, msk, lt)
            yy = py + int((1 - k) * 80)
            A.paste_panel(frame, arr, px, yy, border_alpha=k)
            pop = ease((lt - (1.6 if ok else 0.8)) / 0.35)
            if pop > 0:
                if ok:
                    A.draw_check(frame, px + pw - 80, yy + 90, int(46 * (0.6 + 0.4 * pop)), pop,
                                 ease((lt - 1.7) / 0.5))
                else:
                    A.draw_x(frame, px + pw - 80, yy + 90, int(46 * (0.6 + 0.4 * pop)), pop)

    A.draw_events(frame, gi / FPS)
    if lt < 0.12 and gi > 0:
        a = int(140 * (1 - lt / 0.12))
        frame.alpha_composite(Image.new("RGBA", frame.size, (255, 255, 255, a)))
    return frame.convert("RGB").tobytes()


def timeline(scenes, total):
    """نفس منطق anim_short مع تعديل مواضع النصوص للوحات الجانبية."""
    A.LAY["left"] = SIDE_L
    A.LAY["right"] = SIDE_R
    conv = []
    for sc in scenes:
        s = dict(sc)
        if s["kind"] == "form":
            s["kind"] = "grip"                # نفس تخطيط اللوحتين
        elif s["kind"] == "cta":
            s["kind"] = "sets"                # الرقم الكبير + العنوان
        conv.append(s)
    return A.build_timeline(conv, total)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(config.OUT / "biceps-curl-short.mp4"))
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--preview", type=float, default=None)
    args = ap.parse_args()

    work = config.OUT / "img_work"
    work.mkdir(parents=True, exist_ok=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    SC = EXERCISE["scenes"]

    voices = None
    if not args.no_voice and args.preview is None:
        try:
            A.SCENES = SC
            voices = A.make_voice(work)
        except Exception as e:                             # noqa: BLE001
            print(f"  ! تعذّر التعليق الصوتي ({e}) — نكمل بالموسيقى والترجمة فقط")
    scenes, t = [], 0.0
    for i, sc in enumerate(SC):
        d, extra = sc["min"], {}
        if voices:
            d = max(d, voices[i]["dur"] + 0.45)
            extra = {"words": voices[i]["words"], "vdur": voices[i]["dur"]}
        scenes.append({**sc, **extra, "start": t, "dur": d})
        t += d
    if t < A.TARGET:
        f, t = A.TARGET / t, 0.0
        for sc in scenes:
            sc["dur"] *= f
            sc["start"] = t
            t += sc["dur"]
    total = t
    print(f"• المدة: {total:.1f} ثانية")
    tl = timeline(scenes, total)
    A._init_worker(tl)

    if args.preview is not None:
        sc = next(s for s in scenes if args.preview < s["start"] + s["dur"])
        raw = render_frame((int(args.preview * FPS), sc["kind"], args.preview - sc["start"], sc["dur"]))
        p = work / f"preview_{args.preview:.1f}.png"
        Image.frombytes("RGB", (W, H), raw).save(p)
        print(p)
        return

    n = int(round(total * FPS))
    jobs = []
    for gi in range(n):
        tt = gi / FPS
        sc = next((s for s in scenes if tt < s["start"] + s["dur"]), scenes[-1])
        jobs.append((gi, sc["kind"], tt - sc["start"], sc["dur"]))
    silent = work / "frames.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                            "-preset", "medium", "-crf", "19", "-profile:v", "high",
                            "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    print(f"• رسم {n} إطاراً…")
    with Pool(args.workers, A._init_worker, (tl,)) as pool:
        for i, raw in enumerate(pool.imap(render_frame, jobs, chunksize=4)):
            enc.stdin.write(raw)
            if i % 150 == 0:
                print(f"  {i}/{n}", flush=True)
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError("فشل ترميز الإطارات")

    music = work / "music.wav"
    A.synth_music(music, total + 0.3, [s["start"] for s in scenes[1:]])
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(music)]
    if voices:
        for v in voices:
            cmd += ["-i", str(v["file"])]
        parts = [f"[{i + 2}:a]aresample=44100,adelay={int((s['start'] + 0.15) * 1000)}|"
                 f"{int((s['start'] + 0.15) * 1000)},apad[v{i}]" for i, s in enumerate(scenes)]
        fc = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(len(scenes))) + \
            f"amix=inputs={len(scenes)}:normalize=0:duration=longest,atrim=0:{total + 0.3:.2f},asplit=2[vo][sc];" \
            "[1:a]volume=-13dB[m];[m][sc]sidechaincompress=threshold=0.04:ratio=8:attack=10:release=300[md];" \
            "[vo][md]amix=inputs=2:normalize=0:duration=first[aout]"
    else:
        fc = "[1:a]volume=-4dB[aout]"
    cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-t", f"{total:.3f}",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-3000:])
        raise RuntimeError("فشل المونتاج النهائي")

    meta = {"title": EXERCISE["meta_title"],
            "description": EXERCISE["meta_desc"] + f"\n\nموقعنا الرسمي: https://{config.SITE}",
            "tags": EXERCISE["tags"], "format": "shorts", "duration": round(total, 2),
            "video": out.name, "voice": bool(voices)}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ جاهز: {out} ({out.stat().st_size / 1e6:.1f}MB, {total:.1f}s, صوت: {bool(voices)})")


if __name__ == "__main__":
    main()
