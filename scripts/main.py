"""مصنع الفيديو — نقطة التشغيل الرئيسية.

الاستعمال:
    python scripts/main.py --format shorts
    python scripts/main.py --format long --topic "أفضل 5 تمارين للبطن"
"""
import argparse
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ai          # noqa: E402
import config      # noqa: E402
import render      # noqa: E402
import stock       # noqa: E402
import subs        # noqa: E402
import voice       # noqa: E402

EN = config.CHANNEL_LANG == "en"
QUEUE = config.ROOT / "topics" / ("queue_en.txt" if EN else "queue.txt")
DONE = config.ROOT / "topics" / ("done_en.txt" if EN else "done.txt")


# مواضيع احتياطية دائمة: تُستعمل فقط إذا فرغت القائمة وفشل Gemini،
# ويُختار أول موضوع لم يُنشر من قبل حتى لا يتكرر نفس الفيديو.
EVERGREEN_AR = [
    "ثلاثة تمارين منزلية لشد عضلات البطن",
    "أخطاء في الأكل تمنعك من خسارة الدهون",
    "تمرين خمس دقائق لتنشيط الجسم في الصباح",
    "كيف تبدأ التمرين في البيت بدون معدات",
    "عادات يومية بسيطة تساعدك على خسارة الوزن",
    "أفضل تمارين لتقوية الظهر للمبتدئين",
    "كيف تقلل السكر بدون أن تشعر بالحرمان",
    "تمارين تمدد سريعة بعد يوم طويل من الجلوس",
    "كيف تتجنب الأكل العاطفي في الليل",
    "تمرين كامل للجسم بدون قفز مناسب للجيران",
    "كم خطوة تحتاج يومياً لحرق الدهون",
    "وجبة فطور صحية تشبعك حتى الظهر",
    "تمارين للذراعين بدون أوزان",
    "كيف تحسب حاجتك من السعرات ببساطة",
    "ثلاث خرافات شائعة عن خسارة الوزن",
]
EVERGREEN_EN = [
    "3 home exercises to tighten your core",
    "Eating mistakes that stop your fat loss",
    "A 5 minute morning routine to wake up your body",
    "How to start working out at home with zero equipment",
    "Simple daily habits that help you lose weight",
    "The best back exercises for beginners",
    "How to cut sugar without feeling deprived",
    "Quick stretches after a long day of sitting",
    "How to stop emotional eating at night",
    "A quiet no jump full body workout for apartments",
    "How many steps a day you really need for fat loss",
    "A healthy breakfast that keeps you full until lunch",
    "Arm exercises with no weights",
    "How to work out your calorie needs the simple way",
    "3 common weight loss myths you should stop believing",
]


def _done_topics() -> list:
    if not DONE.exists():
        return []
    return [l.split("|", 1)[-1].strip() for l in DONE.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def next_topic() -> str:
    done = _done_topics()
    done_set = {t.lower() for t in done}
    if QUEUE.exists():
        lines = [l.strip() for l in QUEUE.read_text(encoding="utf-8").splitlines()]
        lines = [l for l in lines if l and not l.startswith("#")]
        for l in lines:
            if l.lower() not in done_set:
                return l
            print(f"  تخطّي موضوع منشور سابقاً: {l}")
            pop_topic(l, log=False)
    # القائمة فارغة: نطلب من Gemini موضوعاً جديداً لم يُستعمل من قبل (محاولتان)
    for attempt in range(2):
        try:
            t = ai.new_topic(done[-60:])
            if t and t.lower() not in done_set:
                print(f"  القائمة فارغة — موضوع جديد من Gemini: {t}")
                return t
        except Exception as e:
            print(f"  تعذّر توليد موضوع تلقائي (محاولة {attempt + 1}): {e}")
    for t in (EVERGREEN_EN if EN else EVERGREEN_AR):
        if t.lower() not in done_set:
            print(f"  موضوع احتياطي: {t}")
            return t
    # كل الاحتياطي استُعمل: نضيف التاريخ حتى لا يتطابق العنوان حرفياً
    base = EVERGREEN_EN[0] if EN else EVERGREEN_AR[0]
    return f"{base} {datetime.now(timezone.utc):%Y-%m-%d}"


def pop_topic(topic: str, log: bool = True):
    if not QUEUE.exists():
        if log:
            with open(DONE, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now(timezone.utc):%Y-%m-%d} | {topic}\n")
        return
    lines = QUEUE.read_text(encoding="utf-8").splitlines()
    kept, removed = [], False
    for l in lines:
        if not removed and l.strip() == topic:
            removed = True
            continue
        kept.append(l)
    QUEUE.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    if not log:
        return
    with open(DONE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc):%Y-%m-%d} | {topic}\n")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return (text[:40] or "video").lower()


def trim_to_target(scenes: list, fmt: str) -> list:
    """يقصّ المشاهد الزائدة إذا تجاوز الفيديو المدة المستهدفة."""
    limit = config.FORMATS[fmt]["target_seconds"] * 1.35
    total, keep = 0.0, []
    for sc in scenes:
        if keep and total + sc["duration"] > limit:
            break
        keep.append(sc)
        total += sc["duration"]
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", default="shorts", choices=["shorts", "long"])
    ap.add_argument("--topic", default=None)
    args = ap.parse_args()

    if not config.GEMINI_API_KEY:
        sys.exit("✗ ناقص GEMINI_API_KEY")
    if not config.PEXELS_API_KEY:
        sys.exit("✗ ناقص PEXELS_API_KEY")

    fmt = args.format
    topic = args.topic or next_topic()
    print(f"\n=== الموضوع: {topic}  |  الصيغة: {fmt} ===\n")

    if config.WORK.exists():
        shutil.rmtree(config.WORK)
    config.WORK.mkdir(parents=True, exist_ok=True)
    config.OUT.mkdir(parents=True, exist_ok=True)

    print("• كتابة السكربت (Gemini)…")
    data = ai.generate(topic, fmt)
    print(f"  العنوان: {data['title']}")

    print("• التعليق الصوتي (edge-tts)…")
    scenes = voice.narrate(data["scenes"], config.WORK)
    scenes = trim_to_target(scenes, fmt)

    print("• جلب اللقطات (Pexels)…")
    scenes = stock.fetch(scenes, config.FORMATS[fmt]["orientation"], config.WORK)

    voice_file = config.WORK / "voice.mp3"
    total = voice.concat_audio(scenes, voice_file)
    print(f"• المدة الإجمالية: {total:.1f} ثانية")

    ass = subs.build(scenes, fmt, config.WORK / "subs.ass")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    name = f"{fmt}-{stamp}-{slugify(topic)}"
    video = config.OUT / f"{name}.mp4"
    thumb = config.OUT / f"{name}.jpg"

    render.build(scenes, fmt, ass, voice_file, total, config.WORK, video)
    render.thumbnail(video, data["thumbnail_text"], fmt, config.WORK, thumb)

    desc = data["description"].strip()
    if config.SITE not in desc:
        desc += (f"\n\nOfficial website: https://{config.SITE}" if EN
                 else f"\n\nموقعنا الرسمي: https://{config.SITE}")
    lead = config.LEAD_MAGNET_URL
    if lead and lead not in desc:
        desc = ((f"FREE 30-day home workout plan: {lead}\n\n" if EN
                 else f"احصل مجاناً على جدول تمارين 30 يوم في البيت: {lead}\n\n") + desc)
    if fmt == "shorts":
        data["title"] = (data["title"][:85] + " #shorts")

    meta = {
        "title": data["title"],
        "description": desc,
        "tags": data["tags"],
        "format": fmt,
        "topic": topic,
        "duration": round(total, 2),
        "video": video.name,
        "thumbnail": thumb.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "categoryId": config.YT_CATEGORY,
        "privacyStatus": config.YT_PRIVACY,
        "lead_magnet_url": lead,
        "pinned_comment": ((f"Want a simple plan? Grab the FREE 30-day home workout plan here: {lead}" if EN
                            else f"تبي خطة واضحة؟ حمّل جدول 30 يوم مجاناً من هنا: {lead}") if lead else ""),
    }
    (config.OUT / f"{name}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (config.OUT / "latest.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.topic:
        pop_topic(topic)

    size = video.stat().st_size / 1e6
    print(f"\n✓ جاهز: {video.name} ({size:.1f}MB, {total:.0f}s)")
    print(f"✓ صورة مصغرة: {thumb.name}")

    gh = Path("/tmp/gh_out")
    with open(gh, "w", encoding="utf-8") as f:
        f.write(f"name={name}\n")


if __name__ == "__main__":
    main()
