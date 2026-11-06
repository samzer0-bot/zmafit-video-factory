"""نشر الفيديو القصير تلقائياً على إنستغرام ريلز وتيك توك (وبنترست اختيارياً) عبر Metricool.

يعمل فقط إذا ضُبط السر METRICOOL_TOKEN (من Metricool: Settings > API).
أي خطأ هنا يُطبع فقط ولا يوقف مصنع الفيديو.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://app.metricool.com/api/v2/scheduler/posts"
TZ = "UTC"


def hashtags(tags, n=8):
    out = []
    for t in tags:
        t = "".join(ch for ch in t if ch.isalnum())
        if t and t.lower() not in {x.lower() for x in out}:
            out.append(t)
    return " ".join("#" + t for t in out[:n])


def main():
    token = os.environ.get("METRICOOL_TOKEN", "").strip()
    if not token:
        print("METRICOOL_TOKEN not set — skipping cross-post")
        return
    m = json.load(open("out/latest.json", encoding="utf-8"))
    video = os.environ.get("VIDEO_URL", "")
    if not video:
        print("no video url — skipping")
        return

    title = m["title"].replace("#shorts", "").strip()
    lead = os.environ.get("LEAD_MAGNET_URL_EN", "").strip()
    cta = "Free 30-day home workout plan: link in bio" if lead else "Follow for a new home workout tip every day"
    text = f"{title}\n\n{cta}\n\n{hashtags(m.get('tags', []))} #homeworkout #fatloss #fitness"[:2100]

    nets = [n.strip() for n in os.environ.get("METRICOOL_NETWORKS", "instagram,tiktok").split(",") if n.strip()]
    board = os.environ.get("METRICOOL_PIN_BOARD", "").strip()
    if "pinterest" in nets and not board:
        nets.remove("pinterest")

    when = datetime.now(timezone.utc) + timedelta(minutes=20)
    body = {
        "text": text,
        "publicationDate": {"dateTime": when.strftime("%Y-%m-%dT%H:%M:00"), "timezone": TZ},
        "providers": [{"network": n} for n in nets],
        "media": [video],
        "autoPublish": True,
        "draft": False,
        "firstCommentText": (f"Grab the free plan here: {lead}" if lead else ""),
        "shortener": False,
        "smartLinkData": {"ids": []},
        "descendants": [],
        "mediaAltText": [],
        "hasNotReadNotes": False,
    }
    if "instagram" in nets:
        body["instagramData"] = {"type": "REEL", "showReelOnFeed": True, "isAiGenerated": True}
    if "tiktok" in nets:
        body["tiktokData"] = {"privacyOption": "PUBLIC_TO_EVERYONE", "title": title[:90], "isAigc": True}
    if "pinterest" in nets:
        body["pinterestData"] = {"boardId": board, "pinTitle": title[:95],
                                 "pinLink": lead or "https://zmafit.com", "isAiGenerated": True}

    q = urllib.parse.urlencode({"blogId": os.environ.get("METRICOOL_BLOG_ID", ""),
                                "userId": os.environ.get("METRICOOL_USER_ID", "")})
    req = urllib.request.Request(f"{API}?{q}", data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "X-Mc-Auth": token})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            print("Metricool:", r.status, r.read().decode("utf-8", "replace")[:300])
    except urllib.error.HTTPError as e:
        print("Metricool HTTP", e.code, e.read().decode("utf-8", "replace")[:500])
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print("Metricool error:", e)
        sys.exit(0)


if __name__ == "__main__":
    main()
