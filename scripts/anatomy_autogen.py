"""مصنع الرسومات التلقائي: تمارين جديدة → رسم بـ Cloudflare (مجاني) → فحص Gemini Vision → إضافة للمكتبة.

    python scripts/anatomy_autogen.py [عدد التمارين=2]

- Gemini يقترح تمارين منزلية غير موجودة في المكتبة (ويتجنب ما فشل مرتين).
- Cloudflare Workers AI (FLUX.2 klein) يرسم نسختين لكل تمرين بأسلوب الرسم المرجعي.
- Gemini Vision يحكم: هل الوضعية صحيحة؟ وأين العضلات الملوّنة؟ (مربعات → نقاط مرجعية تلقائية)
  العضلات الملوّنة خطأً تُخفى عن الوكيل ("_" في البداية).
- المقبول يُحفظ في assets/anatomy + poses.json + catalog.json، وكل محاولة تُسجَّل في autogen_log.json.
"""
import base64, io, json, os, re, sys, time, urllib.request, uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai, config                                  # noqa: E402

A = config.ASSETS / "anatomy"
POSES, CAT, LOG = A / "poses.json", A / "catalog.json", A / "autogen_log.json"
OUT = Path("autogen_out"); OUT.mkdir(exist_ok=True)
CF_ACC = os.environ.get("CF_ACCOUNT_ID", ""); CF_TOK = os.environ.get("CF_API_TOKEN", "")
MUSCLES = ["chest", "delts", "biceps", "triceps", "forearms", "abs", "obliques", "lats", "traps", "lower_back",
           "glutes", "hamstrings", "quads", "adductors", "hip_flexors", "calves"]
STYLE = ("Detailed anatomical pencil illustration in the exact style of the reference image: the whole man is drawn in fine "
         "graphite cross-hatching, grayscale, showing every muscle fiber like a medical anatomy atlas. Same man as the reference: "
         "athletic, short buzz cut, short beard, black athletic shorts, black running sneakers with white soles. "
         "ONLY the working muscles listed are colored in vivid flat red-orange (same red-orange as the reference) with the fiber "
         "texture visible through the color; every other muscle stays grayscale. Pure plain white background, full body visible, "
         "centered, generous even margins. No text, no labels, no arrows, no watermark, no logo.")


def jload(p, default):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return default


def ask_json(parts, tokens=4096):
    payload = {"contents": [{"parts": parts}],
               "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json", "maxOutputTokens": tokens}}
    for _ in range(3):
        out = ai.ask(payload)
        txt = "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"])
        try: return json.loads(re.sub(r"^```(json)?|```$", "", txt.strip()))
        except Exception as e: print("  ! JSON:", e)
    raise RuntimeError("no JSON")


def propose(n, cat, log):
    failed = [k for k, v in log.items() if v.get("fails", 0) >= 2]
    have = {k: v["desc"] for k, v in cat.items()}
    d = ask_json([{"text": f"""We have anatomy drawings of these home/bodyweight exercises: {json.dumps(have)}.
Already tried and failed (do NOT propose): {failed}.
Propose {n} NEW, popular, trending home exercises (no gym machines) that are easy to draw as ONE clear static frame
(prefer standing, kneeling, or simple floor positions; avoid hanging, complex twists, equipment other than a bench/box/wall).
Return JSON: {{"exercises": [{{"id": "short_snake_case_id", "name": "Exercise name",
"aspect": "portrait or landscape", "pose": "precise single-frame body position, which way he faces, what touches the floor",
"view": "front / side / back / three-quarter", "muscles": ["2-3 ids from {MUSCLES}"]}}]}}"""}])
    out = []
    for e in d.get("exercises", []):
        eid = re.sub(r"[^a-z0-9_]", "", str(e.get("id", "")).lower())[:20]
        if eid and eid not in cat and eid not in failed and eid not in [x["id"] for x in out]:
            e["id"] = eid; e["muscles"] = [m for m in e.get("muscles", []) if m in MUSCLES] or ["quads"]
            out.append(e)
    return out[:n]


def cloudflare(e, seed, dest):
    ref = Image.open(A / "front.jpg").convert("RGB"); ref.thumbnail((500, 500))
    buf = io.BytesIO(); ref.save(buf, "PNG")
    w, h = (768, 1344) if e.get("aspect") == "portrait" else (1344, 768)
    prompt = (f"Use image 0 only as the style and character reference. {STYLE} Exercise: {e['name']}. "
              f"Pose ({e.get('view', 'side')} view): {e['pose']}. Red muscles: {', '.join(e['muscles'])}.")
    b = uuid.uuid4().hex; body = b""
    for k, v in {"prompt": prompt, "width": str(w), "height": str(h), "seed": str(seed)}.items():
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += (f"--{b}\r\nContent-Disposition: form-data; name=\"input_image_0\"; filename=\"ref.png\"\r\n"
             f"Content-Type: image/png\r\n\r\n").encode() + buf.getvalue() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/ai/run/@cf/black-forest-labs/flux-2-klein-4b",
                                 data=body, headers={"Authorization": f"Bearer {CF_TOK}", "Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            img = (json.loads(r.read()).get("result") or {}).get("image")
        if img:
            dest.write_bytes(base64.b64decode(img)); return True
    except Exception as ex:
        print("  cloudflare failed:", ex, getattr(ex, "read", lambda: b"")()[:200])
    return False


def red_mask(im):
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    return (r > g * 1.3) & (r > b * 1.3) & ((mx - mn) / (mx + 1e-6) > 0.30)


def review(e, path):
    """Gemini Vision: صحة الوضعية + أماكن العضلات الملوّنة."""
    im = Image.open(path).convert("RGB"); W, H = im.size
    small = im.copy(); small.thumbnail((1024, 1024)); buf = io.BytesIO(); small.save(buf, "JPEG", quality=88)
    d = ask_json([{"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}},
                  {"text": f"""You are a strict strength coach reviewing an anatomy drawing meant to show the exercise
"{e['name']}": {e['pose']}.
1) pose_correct: true ONLY if the body position clearly and correctly shows this exercise with good form
   (a viewer could copy it safely). Wrong exercise, sitting/lying instead of the right position, missing key joint angles = false.
2) style_ok: grayscale pencil anatomy drawing, man, red-orange colored muscles, white background, no text.
3) muscles: EVERY red/orange colored region; name from {MUSCLES}; box_2d = [ymin, xmin, ymax, xmax] normalized 0-1000;
   worked = true only if that muscle genuinely works in this exercise.
Return JSON: {{"pose_correct": bool, "pose_issue": "short", "style_ok": bool, "muscles": [{{"name": "", "box_2d": [0,0,0,0], "worked": bool}}]}}"""}])
    red = red_mask(im); ys, xs = np.nonzero(red)
    seeds = {}
    if len(xs):
        for m in d.get("muscles", []):
            try:
                y0, x0, y1, x1 = [float(v) for v in m["box_2d"]]
            except Exception: continue
            cx, cy = (x0 + x1) / 2000 * W, (y0 + y1) / 2000 * H
            box = red[int(y0 / 1000 * H):int(y1 / 1000 * H) + 1, int(x0 / 1000 * W):int(x1 / 1000 * W) + 1]
            if box.sum() < 300: continue                     # لا يوجد لون أحمر داخل المربع
            i = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))  # نلصق النقطة بأقرب بكسل أحمر
            name = m.get("name") if m.get("name") in MUSCLES else "other"
            key = name if m.get("worked") else "_" + name
            seeds.setdefault(key, []).append([int(xs[i]), int(ys[i])])
    worked = [k for k in seeds if not k.startswith("_")]
    ok = bool(d.get("pose_correct")) and bool(d.get("style_ok")) and len(worked) >= 1
    return ok, d, seeds


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    if not (CF_ACC and CF_TOK): sys.exit("✗ CF_ACCOUNT_ID / CF_API_TOKEN غير موجودة")
    poses, cat, log = jload(POSES, {}), jload(CAT, {}), jload(LOG, {})
    added = []
    for e in propose(n, cat, log):
        print(f"• {e['id']} — {e['name']} | {e['muscles']}")
        best = None
        for v in range(2):
            p = OUT / f"{e['id']}_{v + 1}.png"
            if not cloudflare(e, int(time.time()) % 100000 + v, p): continue
            ok, d, seeds = review(e, p)
            print(f"  نسخة {v + 1}: {'✓ مقبولة' if ok else '✗ مرفوضة'} — {d.get('pose_issue', '')} | {list(seeds)}")
            (OUT / f"{e['id']}_{v + 1}.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            if ok and (best is None or len(seeds) > len(best[1])): best = (p, seeds)
            if ok: break
        rec = log.setdefault(e["id"], {"name": e["name"], "fails": 0})
        rec["last"] = datetime.now(timezone.utc).isoformat()
        if best:
            p, seeds = best
            Image.open(p).convert("RGB").save(A / f"{e['id']}.jpg", quality=93)
            poses[e["id"]] = seeds
            cat[e["id"]] = {"desc": f"{e['name']}: {e['pose']} ({e.get('view', '')} view)",
                            "added": datetime.now(timezone.utc).date().isoformat(), "auto": True}
            rec["status"] = "added"; added.append(e["id"])
        else:
            rec["fails"] += 1; rec["status"] = "rejected"
    POSES.write_text(json.dumps(poses, indent=1), encoding="utf-8")
    CAT.write_text(json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")
    LOG.write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"✓ أُضيف {len(added)}: {added} — المكتبة الآن {len(poses)} رسماً")


if __name__ == "__main__":
    main()
