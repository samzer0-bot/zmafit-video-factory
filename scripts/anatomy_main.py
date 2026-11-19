"""وكيل فيديوهات التشريح: يختار قالباً وموضوعاً جديداً، Gemini يكتب المحتوى، ثم الرندر والصورة المصغرة.

    VIDEO_LANG=ar python scripts/anatomy_main.py --format shorts
    VIDEO_LANG=en python scripts/anatomy_main.py --format long

المخرجات بنفس شكل main.py (out/<name>.mp4/.jpg/.json + out/latest.json) ليرفعها سيناريو Make الحالي.
"""
import argparse, json, random, re, shutil, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config, ai, render                     # noqa: E402
import anatomy_video as AV                     # noqa: E402
import numpy as np                             # noqa: E402
from PIL import Image                          # noqa: E402

LANG = config.CHANNEL_LANG
EN = LANG == "en"
HIST = config.ASSETS / "anatomy" / "history.json"
CATALOG = json.loads((config.ASSETS / "anatomy" / "catalog.json").read_text(encoding="utf-8"))

TEMPLATES = {
 "shorts": ["mistake", "myth", "rank", "compare"],
 "long": ["chapters"],
}
TEMPLATE_GUIDE = {
 "mistake": "WRONG vs RIGHT: alternate beats with verdict 'r' (what people wrongly think works / wrong focus) and 'g' (what really works). 5-7 beats.",
 "myth": "MYTH or FACT: each beat has a short 'claim' sentence (a popular belief) and verdict 'r' if it is a myth or 'g' if it is a fact. 3 claims, at least one myth and one fact.",
 "rank": "RANKED: 3 or 4 beats ranking the muscles an exercise works, from most (#1) to least, all verdict 'g', each with 'rank'. Optionally a last beat with verdict 'r' for a muscle people wrongly expect.",
 "compare": "VERSUS: compare two exercises/poses. Fill 'compare' (left vs right) plus 3-5 beats explaining which muscles each one hits (verdict 'g' or 'r').",
 "chapters": "LONG LESSON (5+ minutes): 3-4 chapters; each beat has a 'chapter' title. 14-20 beats. Each 'say' is 2-4 full sentences of real, specific coaching (form cues, why it works, common mistakes, home variations, sets and reps).",
}


def load_hist():
    try: return json.loads(HIST.read_text(encoding="utf-8"))
    except Exception: return []


def pick_template(fmt, hist):
    mine = [h for h in hist if h["lang"] == LANG and h["format"] == fmt]
    opts = TEMPLATES[fmt][:]
    recent = [h["template"] for h in mine[-(len(opts) - 1):]] if len(opts) > 1 else []
    cand = [t for t in opts if t not in recent] or opts
    return random.choice(cand)


def ask_json(prompt, tokens=16384):
    payload = {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"temperature": 1.0, "responseMimeType": "application/json", "maxOutputTokens": tokens}}
    for attempt in range(4):
        out = ai.ask(payload)
        txt = "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"])
        try:
            return json.loads(re.sub(r"^```(json)?|```$", "", txt.strip()))
        except Exception as e:
            print(f"  ! JSON غير صالح ({e}) — إعادة الطلب {attempt + 1}")
    raise RuntimeError("Gemini لم يُرجع JSON صالحاً")


def gemini_content(template, fmt, hist):
    now = datetime.now(timezone.utc)
    mine = [h["topic"] for h in hist if h["lang"] == LANG][-40:]
    other_recent = [h["topic"] for h in hist if h["lang"] != LANG and
                    datetime.fromisoformat(h["date"]) > now - timedelta(days=10)]
    cat = "\n".join(f"- {k}: {v['desc']} | muscles: {', '.join(AV.POSES.get(k, {}).keys())}" for k, v in CATALOG.items() if k in AV.POSES)
    lang_rules = ("Write ALL on-screen text and narration in natural, energetic Modern Standard Arabic (simple, clear). "
                  "Audience: Arab beginners training at home without equipment."
                  if not EN else
                  "Write ALL text in punchy, natural American English. Audience: busy people training at home.")
    short = fmt == "shorts"
    prompt = f"""You are the head coach and scriptwriter of a fitness YouTube channel ({config.BRAND}, {config.SITE}).
Create ONE {'YouTube Short (25-45 seconds total narration)' if short else 'long YouTube video (5-7 minutes of narration)'} using animated anatomy drawings.
Template: {template.upper()} — {TEMPLATE_GUIDE[template]}

Available drawings (pose id: description | muscles that can be highlighted):
{cat}
Use ONLY these pose ids and ONLY the listed muscle ids for each pose.

Pick a fresh, specific, genuinely useful topic that fits the template and the drawings (an exercise, a muscle, a common mistake or myth).
Inspired by what trends now in home fitness (abs, glutes, triceps, V-taper shoulders, legs, push-ups, squats), but with original angle and wording.
Do NOT reuse these topics of this channel: {mine}
Do NOT use these topics recently covered by our other channel: {other_recent}
{lang_rules}
Accuracy matters: only state anatomy and training facts that are correct and widely accepted. No invented statistics or percentages.

Return JSON only:
{{"topic": "...", "title": "YouTube title, max 80 chars, curiosity + keyword", "description": "2-3 sentences + call to action",
"tags": ["8-12 tags"], "screen_title": "max 3 words", "screen_subtitle": "max 6 words",
"thumb_hook": "1-2 huge words", "thumb_main": "2-4 words", "thumb_tag": "max 2 words",
"hook_text": "max 7 words on screen", "hook_say": "first spoken sentence, a strong hook",
"beats": [{{"pose": "pose id", "muscles": ["muscle ids"], "verdict": "g or r", "label": "max 5 words",
  "note": "max 7 words or empty", "say": "{'one short sentence (max 14 words)' if short else '2-4 sentences'}",
  "claim": "for myth template only", "rank": 0, "chapter": "for long template only"}}],
"compare": {{"left_pose": "", "left_muscles": [], "left_label": "", "right_pose": "", "right_muscles": [], "right_label": "", "say": ""}},
"outro_label": "max 5 words", "outro_say": "closing sentence with a call to subscribe/save", "cta": "max 5 words"}}"""
    if short:
        return ask_json(prompt)
    # الفيديو الطويل على مراحل: خطة الفصول أولاً ثم مشاهد كل فصل (لتفادي قطع الرد)
    plan = ask_json(prompt + """
IMPORTANT for this long video: do NOT write the beats now. Instead return the same JSON but replace "beats" with
"chapters": [{"title": "chapter title", "focus": "what this chapter teaches, which poses and muscles"}] (3-4 chapters).""", 8192)
    beats = []
    for ch in (plan.get("chapters") or [])[:4]:
        part = ask_json(f"""{prompt}

We are writing ONE chapter of this long video. Topic: {plan.get('topic')}. Chapter: {ch.get('title')} — {ch.get('focus')}.
Return JSON only: {{"beats": [4 to 6 beats in the same beat format, each with "chapter": "{ch.get('title')}"]}}""", 8192)
        for b in part.get("beats", []):
            b["chapter"] = ch.get("title", "")
            beats.append(b)
    plan["beats"] = beats
    return plan


def clean_beat(b):
    pose = b.get("pose") if b.get("pose") in AV.POSES else random.choice([p for p in CATALOG if p in AV.POSES])
    ms = [m for m in (b.get("muscles") or []) if m in AV.POSES[pose]] or [next(iter(AV.POSES[pose]))]
    b["pose"], b["muscles"] = pose, ms
    b["verdict"] = "r" if b.get("verdict") == "r" else "g"
    for k in ("label", "note", "say", "claim", "chapter"):
        b[k] = ai.clean(str(b.get(k) or ""))
    b["label"] = re.sub(r"^\s*(No\.?|رقم)?\s*[0-9٠-٩]+\s*[-—:.)]*\s*", "", b["label"])
    return b


def build_scenes(template, c):
    T = ai.clean
    M = {"ar": ("خرافة", "حقيقة"), "en": ("MYTH", "FACT")}[LANG]
    beats = [clean_beat(b) for b in c.get("beats", []) if isinstance(b, dict)]
    if not beats: raise RuntimeError("لا توجد مشاهد")
    sc = []
    first = beats[0]
    if template in ("myth", "compare"):
        sc.append({"type": "card", "kind": "hook", "lines": [T(c.get("hook_text", "")), T(c.get("screen_subtitle", ""))], "say": T(c.get("hook_say", ""))})
    else:
        sc.append({"pose": first["pose"], "focus": "full", "all_red_intro": True, "label": T(c.get("hook_text", "")), "say": T(c.get("hook_say", ""))})
    last_ch = None
    for i, b in enumerate(beats):
        hl = [[m, b["verdict"]] for m in b["muscles"]]
        s = {"pose": b["pose"], "focus": b["muscles"], "hl": hl, "label": b["label"], "icon": "ok" if b["verdict"] == "g" else "no",
             "say": b["say"], "dots": b["verdict"] == "g" and i % 2 == 0, "arrows": b["verdict"] == "r" or i % 2 == 1}
        if b.get("note"): s["note"] = b["note"]; s["note_ok"] = b["verdict"] == "g"
        if template == "myth" and b.get("claim"):
            sc.append({"type": "card", "kind": "fact" if b["verdict"] == "g" else "myth", "lines": [b["claim"]],
                       "icon": s["icon"], "say": b["claim"] + ("؟" if not EN else "?")})
            s["stamp"] = M[1] if b["verdict"] == "g" else M[0]
        if template == "rank" and b["verdict"] == "g":
            s["badge"] = f"#{b.get('rank') or i + 1}"
        if template == "chapters":
            ch = b.get("chapter") or ""
            if ch and ch != last_ch:
                sc.append({"type": "card", "kind": "chapter", "lines": [ch], "say": ""})
                last_ch = ch
            s["chapter"] = ch
        sc.append(s)
        if template == "compare" and i == 0:
            cp = c.get("compare") or {}
            L, R = clean_beat({"pose": cp.get("left_pose"), "muscles": cp.get("left_muscles")}), clean_beat({"pose": cp.get("right_pose"), "muscles": cp.get("right_muscles")})
            sc.append({"type": "split", "center": "VS", "say": T(cp.get("say", "")),
                       "left": {"pose": L["pose"], "focus": "full", "hl": [[m, "g"] for m in L["muscles"]], "label": T(cp.get("left_label", ""))},
                       "right": {"pose": R["pose"], "focus": "full", "hl": [[m, "g"] for m in R["muscles"]], "label": T(cp.get("right_label", ""))}})
    good = [b for b in beats if b["verdict"] == "g"]
    lastp = (good or beats)[-1]["pose"]
    outro_m = sorted({m for b in good if b["pose"] == lastp for m in b["muscles"]}) or beats[-1]["muscles"]
    sc.append({"pose": lastp, "focus": "full", "hl": [[m, "g"] for m in outro_m], "label": T(c.get("outro_label", "")),
               "icon": "ok", "say": T(c.get("outro_say", "")), "cta": T(c.get("cta", ""))})
    for s in sc:                                  # بطاقات بلا كلام: مدة ثابتة
        if not s.get("say"): s["dur"] = 1.6
    return sc


def thumb_photo(c, path):
    """صورة للصورة المصغرة: الرسم مع العضلة الأساسية ملونة."""
    b = clean_beat(dict(c["beats"][0])) if c.get("beats") else {"pose": "front", "muscles": ["chest"]}
    P = AV.pose(b["pose"]); C = AV.Ctx(LANG, "long")
    img = P["gray"]
    for m in b["muscles"]:
        img = AV.tint(img, P["shade"], P["masks"][m], C.T["ok"], .95)
    pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    box = AV.viewport(P, b["muscles"], 16 / 9)
    AV.crop(pil, box, (1280, 720), (245, 245, 245)).save(path, quality=92)
    return path


def slug(t): return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40] or "anatomy"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--format", default="shorts", choices=["shorts", "long"])
    ap.add_argument("--template", default="")
    a = ap.parse_args(); fmt = a.format
    hist = load_hist()
    template = a.template or pick_template(fmt, hist)
    print(f"=== {LANG} | {fmt} | قالب: {template} ===")
    c = gemini_content(template, fmt, hist)
    print("  الموضوع:", c.get("topic"))
    scenes = build_scenes(template, c)
    spec = {"format": "short" if fmt == "shorts" else "long", "lang": LANG,
            "title": ai.clean(c.get("screen_title", "")), "subtitle": ai.clean(c.get("screen_subtitle", "")),
            "brand": config.BRAND.upper(), "site": config.SITE, "scenes": scenes}
    if config.OUT.exists(): shutil.rmtree(config.OUT)
    config.OUT.mkdir(parents=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    name = f"{fmt}-{stamp}-anatomy-{template}-{slug(c.get('topic', '') if EN else template)}"
    video = config.OUT / f"{name}.mp4"; thumb = config.OUT / f"{name}.jpg"
    (config.OUT / f"{name}.spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    AV.render(spec, video, config.WORK / "anat")
    total = AV._dur(video)
    tp = thumb_photo(c, config.WORK / "thumb_src.jpg")
    render.thumbnail(video, c.get("thumb_main", ""), fmt, config.WORK, thumb, parts=c, photo=tp)
    desc = ai.clean(c.get("description", ""))
    if config.SITE not in desc:
        desc += (f"\n\nOfficial website: https://{config.SITE}" if EN else f"\n\nموقعنا الرسمي: https://{config.SITE}")
    lead = config.LEAD_MAGNET_URL
    if lead and lead not in desc:
        desc = ((f"FREE 30-day home workout plan: {lead}\n\n" if EN else f"احصل مجاناً على جدول تمارين 30 يوم في البيت: {lead}\n\n") + desc)
    title = ai.clean(c.get("title", ""))[:90]
    if fmt == "shorts": title = title[:85] + " #shorts"
    meta = {"title": title, "description": desc, "tags": c.get("tags", [])[:15], "format": fmt, "topic": c.get("topic", ""),
            "duration": round(total, 2), "video": video.name, "thumbnail": thumb.name,
            "created_at": datetime.now(timezone.utc).isoformat(), "categoryId": config.YT_CATEGORY,
            "privacyStatus": config.YT_PRIVACY, "lead_magnet_url": lead, "style": f"anatomy-{template}"}
    for p in (config.OUT / f"{name}.json", config.OUT / "latest.json"):
        p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    hist.append({"date": datetime.now(timezone.utc).isoformat(), "lang": LANG, "format": fmt, "template": template,
                 "topic": c.get("topic", ""), "poses": sorted({s.get("pose") for s in scenes if s.get("pose")})})
    HIST.write_text(json.dumps(hist[-300:], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {video.name} ({total:.0f}s)")


if __name__ == "__main__":
    main()
