"""جلب لقطات فيديو مجانية من Pexels (رخصة حرة، بدون حقوق)."""
import json
import random
import urllib.parse
import urllib.request
from pathlib import Path

import config

API = "https://api.pexels.com/videos/search"


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": config.PEXELS_API_KEY})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _pick_file(videos: list, orientation: str, used: set):
    """يختار أفضل ملف فيديو غير مستعمل."""
    want_portrait = orientation == "portrait"
    random.shuffle(videos)
    for v in videos:
        if v["id"] in used:
            continue
        if v.get("duration", 0) < 4:
            continue
        best = None
        for f in v["video_files"]:
            w, h = f.get("width") or 0, f.get("height") or 0
            if not w or not h:
                continue
            is_portrait = h > w
            if is_portrait != want_portrait:
                continue
            if want_portrait and h < 1080:
                continue
            if not want_portrait and w < 1280:
                continue
            # نفضّل الأقرب لـ 1080 لتقليل الحجم
            score = abs((h if want_portrait else w) - (1920 if want_portrait else 1920))
            if best is None or score < best[0]:
                best = (score, f["link"], v["id"], v.get("duration", 10))
        if best:
            return best
    return None


def fetch(scenes: list, orientation: str, workdir: Path) -> list:
    """ينزّل لقطة لكل مشهد."""
    workdir.mkdir(parents=True, exist_ok=True)
    used = set()
    for i, sc in enumerate(scenes):
        queries = [sc["keywords"]] + random.sample(config.FALLBACK_QUERIES, 3)
        chosen = None
        for q in queries:
            url = (f"{API}?query={urllib.parse.quote(q)}"
                   f"&orientation={'portrait' if orientation == 'portrait' else 'landscape'}"
                   f"&per_page=25&size=medium")
            try:
                data = _get(url)
            except Exception as e:                       # noqa: BLE001
                print(f"  ! Pexels فشل على '{q}': {e}")
                continue
            got = _pick_file(data.get("videos", []), orientation, used)
            if got:
                chosen = got
                break
        if not chosen:
            raise RuntimeError(f"لم يُعثر على لقطة للمشهد {i} ({sc['keywords']})")

        _, link, vid, dur = chosen
        used.add(vid)
        dest = workdir / f"clip_{i:02d}.mp4"
        urllib.request.urlretrieve(link, dest)
        sc["clip"] = str(dest)
        sc["clip_duration"] = dur
        print(f"  ✓ لقطة {i + 1}: pexels#{vid} ({dest.stat().st_size // 1024}KB)")
    return scenes
