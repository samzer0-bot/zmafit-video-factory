"""جلب لقطات فيديو مجانية من Pexels (رخصة حرة، بدون حقوق)."""
import json
import random
import shutil
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import config

API = "https://api.pexels.com/videos/search"

BROAD = [
    "fitness", "workout", "gym", "exercise", "training",
    "running", "healthy lifestyle", "sport", "stretching", "yoga",
]


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": config.PEXELS_API_KEY})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _best_file(v: dict, want_portrait: bool, min_side: int):
    """يختار أفضل ملف داخل فيديو واحد."""
    best = None
    for f in v.get("video_files", []):
        w, h = f.get("width") or 0, f.get("height") or 0
        if not w or not h:
            continue
        if max(w, h) < min_side:
            continue
        right_orient = (h > w) == want_portrait
        long_side = h if want_portrait else w
        prio = (0 if right_orient else 1, abs(long_side - 1920))
        if best is None or prio < best[0]:
            best = (prio, f["link"])
    return best


def _search(query: str, orientation, want_portrait: bool, used: set, min_side: int):
    params = {"query": query, "per_page": "40"}
    if orientation:
        params["orientation"] = orientation
    url = f"{API}?{urllib.parse.urlencode(params)}"
    try:
        data = _get(url)
    except urllib.error.HTTPError as e:
        print(f"    Pexels HTTP {e.code} على '{query}'")
        return None
    except Exception as e:
        print(f"    Pexels خطأ على '{query}': {e}")
        return None

    vids = [v for v in data.get("videos", []) if v["id"] not in used]
    if not vids:
        return None
    random.shuffle(vids)

    best = None
    for v in vids:
        got = _best_file(v, want_portrait, min_side)
        if got and (best is None or got[0] < best[0]):
            best = (got[0], got[1], v["id"], v.get("duration", 10))
            if got[0][0] == 0:
                break
    return best


def fetch(scenes: list, orientation: str, workdir: Path) -> list:
    """ينزّل لقطة لكل مشهد، مع سلسلة بدائل حتى لا يفشل الإنتاج."""
    workdir.mkdir(parents=True, exist_ok=True)
    want_portrait = orientation == "portrait"
    orient_param = "portrait" if want_portrait else "landscape"
    used = set()
    downloaded = []

    for i, sc in enumerate(scenes):
        kw = sc["keywords"]
        first_word = kw.split()[0] if kw.split() else "fitness"
        broad = random.sample(BROAD, 5)

        attempts = [
            (kw, orient_param, 1080),
            (kw, orient_param, 720),
            (first_word, orient_param, 720),
            (kw, None, 720),
        ]
        attempts += [(q, orient_param, 720) for q in broad]
        attempts += [(q, None, 640) for q in broad[:3]]

        chosen = None
        for q, orient, min_side in attempts:
            chosen = _search(q, orient, want_portrait, used, min_side)
            if chosen:
                break

        if not chosen:
            if downloaded:
                src = random.choice(downloaded)
                dest = workdir / f"clip_{i:02d}.mp4"
                shutil.copy(src, dest)
                sc["clip"] = str(dest)
                sc["clip_duration"] = 10
                print(f"  ~ لقطة {i + 1}: أُعيد استعمال لقطة سابقة (لا نتائج لـ '{kw}')")
                continue
            raise RuntimeError(
                f"لم يُعثر على أي لقطة للمشهد {i} ('{kw}'). "
                "تحقّق من صلاحية PEXELS_API_KEY."
            )

        _, link, vid, dur = chosen
        used.add(vid)
        dest = workdir / f"clip_{i:02d}.mp4"
        try:
            urllib.request.urlretrieve(link, dest)
        except Exception as e:
            print(f"  ! فشل تنزيل لقطة {i + 1}: {e}")
            if downloaded:
                shutil.copy(random.choice(downloaded), dest)
            else:
                raise
        sc["clip"] = str(dest)
        sc["clip_duration"] = dur
        downloaded.append(dest)
        print(f"  ✓ لقطة {i + 1}: pexels#{vid} ({dest.stat().st_size // 1024}KB)")

    return scenes
