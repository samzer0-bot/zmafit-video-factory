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

QUEUE = config.ROOT / "topics" / "queue.txt"
DONE = config.ROOT / "topics" / "done.txt"


def next_topic() -> str:
    if QUEUE.exists():
        lines = [l.strip() for l in QUEUE.read_text(encoding="utf-8").splitlines()]
        lines = [l for l in lines if l and not l.startswith("#")]
        if lines:
            return lines[0]
    return "نصيحة سريعة لحرق دهون البطن بدون معدات"


def pop_topic(topic: str):
    if not QUEUE.exists():
        return
    lines = QUEUE.read_text(encoding="utf-8").splitlines()
    kept, removed = [], False
    for l in lines:
        if not removed and l.strip() == topic:
            removed = True
            continue
        kept.append(l)
    QUEUE.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    with open(DONE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc):%Y-%m-%d} | {topic}\n")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w؀-ۿ]+", "-", text).strip("-")
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
        desc += f"\n\nمزيد من البرامج والكتب: https://{config.SITE}"
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
