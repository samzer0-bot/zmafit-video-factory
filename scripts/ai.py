"""توليد سكربت الفيديو بالعربية عبر Gemini (الباقة المجانية)."""
import json
import os
import re
import time
import urllib.request
import urllib.error

import config

BASE = "https://generativelanguage.googleapis.com/v1beta"

MODEL_CANDIDATES = [
    os.environ.get("GEMINI_MODEL", ""),
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

_MODELS = None
RETRY_CODES = (429, 500, 502, 503, 504)
BACKOFF = [8, 20, 45]


class Busy(Exception):
    """الخادم مشغول مؤقتاً — يستحق إعادة المحاولة."""


SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "thumbnail_text": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string"},
                    "keywords": {"type": "string"},
                },
                "required": ["narration", "keywords"],
            },
        },
    },
    "required": ["title", "description", "tags", "thumbnail_text", "scenes"],
}

PROMPT = """أنت كاتب محتوى لقناة يوتيوب عربية اسمها {brand} متخصصة في اللياقة البدنية وخسارة الدهون والتمارين المنزلية.

اكتب سكربت فيديو {kind} عن الموضوع التالي:
«{topic}»

القواعد الصارمة:
- اللغة: عربية فصحى مبسّطة، سهلة الفهم لجمهور من الجزائر ومصر والسعودية.
- المشهد الأول = خطّاف (hook) قوي في جملة واحدة قصيرة توقف المتفرج فوراً.
- {n} مشاهد بالضبط.
- كل مشهد: جملة أو جملتين فقط، بحدود {wps} كلمة، لأنها ستُقرأ بصوت آلي.
- المشهد الأخير = دعوة للاشتراك في القناة وزيارة {site}.
- ممنوع نهائياً: الرموز التعبيرية، الأقواس، علامات النجمة، أي رموز تنسيق. نص منطوق نظيف فقط.
- ممنوع الوعود الطبية أو ادعاءات علاجية. نصائح عامة آمنة فقط.
- لكل مشهد ضع "keywords": 2-4 كلمات بالإنجليزية تصف اللقطة المرئية المناسبة للبحث في مكتبة فيديوهات (مثال: "man doing push ups gym").

كذلك أعطني:
- title: عنوان يوتيوب عربي جذاب أقل من 70 حرفاً.
- description: وصف من 3 أسطر بالعربية + سطر فيه رابط {site}.
- tags: 12 وسماً مختلطة عربي وإنجليزي.
- thumbnail_text: 3 إلى 5 كلمات عربية فقط للصورة المصغرة.
"""


def _post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        if e.code in RETRY_CODES:
            raise Busy(f"HTTP {e.code}") from None
        raise RuntimeError(f"Gemini HTTP {e.code}: {body}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise Busy(f"شبكة: {e}") from None


def _get(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:600]
        raise RuntimeError(f"Gemini HTTP {e.code}: {body}") from None


def _score(name: str) -> int:
    """كلما صغر الرقم كان الموديل أنسب."""
    bad = ("tts", "image", "vision", "embedding", "live", "native-audio",
           "thinking", "learnlm", "gemma")
    if any(b in name for b in bad):
        return 100
    if "flash-lite" in name:
        return 3
    if "flash" in name:
        return 1
    if "pro" in name:
        return 2
    return 50


def rank_models(available: list) -> list:
    """يرتّب الموديلات الصالحة: المفضّلة أولاً ثم البقية حسب الأنسب."""
    usable = [
        m["name"].split("/")[-1] for m in available
        if "generateContent" in (m.get("supportedGenerationMethods") or [])
    ]
    if not usable:
        raise RuntimeError("لا يوجد أي موديل يدعم generateContent في هذا الحساب")

    ordered = [c for c in MODEL_CANDIDATES if c and c in usable]
    rest = sorted((m for m in usable if m not in ordered),
                  key=lambda n: (_score(n), len(n)))
    ordered += [m for m in rest if _score(m) < 100]

    if not ordered:
        raise RuntimeError(f"لا يوجد موديل نصي مناسب. المتاح: {usable[:15]}")
    return ordered[:5]


def models() -> list:
    global _MODELS
    if _MODELS is None:
        data = _get(f"{BASE}/models?key={config.GEMINI_API_KEY}&pageSize=200")
        _MODELS = rank_models(data.get("models", []))
        print(f"  الموديلات المتاحة بالترتيب: {_MODELS}")
    return _MODELS


def ask(payload: dict) -> dict:
    """يجرّب كل موديل مع إعادة محاولة عند ازدحام الخادم."""
    last = None
    for model in models():
        url = f"{BASE}/models/{model}:generateContent?key={config.GEMINI_API_KEY}"
        for attempt, wait in enumerate([0] + BACKOFF):
            if wait:
                print(f"  الخادم مشغول — إعادة المحاولة بعد {wait}s ({model})")
                time.sleep(wait)
            try:
                out = _post(url, payload)
                print(f"  الموديل المستعمل: {model}")
                return out
            except Busy as e:
                last = e
            except RuntimeError as e:
                last = e
                break
        print(f"  تعذّر {model} ({last}) — ننتقل للموديل التالي")
    raise RuntimeError(f"فشل كل الموديلات. آخر خطأ: {last}")


def clean(text: str) -> str:
    """يزيل الرموز التي تُفسد النطق الآلي."""
    text = re.sub(r"[*_#`~<>\[\]{}|]", " ", text)
    text = re.sub(r"[\U0001F000-\U0001FAFF☀-➿]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def generate(topic: str, fmt: str = "shorts") -> dict:
    cfg = config.FORMATS[fmt]
    kind = "قصير عمودي (Shorts) مدته حوالي 45 ثانية" if fmt == "shorts" else "أفقي مدته حوالي 4 دقائق"
    wps = 14 if fmt == "shorts" else 30

    prompt = PROMPT.format(
        brand=config.BRAND, kind=kind, topic=topic,
        n=cfg["scenes"], wps=wps, site=config.SITE,
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
        },
    }

    raw = ask(payload)
    text = raw["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(text)

    data["title"] = clean(data["title"])[:95]
    data["description"] = clean(data["description"])
    data["thumbnail_text"] = clean(data["thumbnail_text"])
    data["tags"] = [clean(t)[:30] for t in data["tags"]][:15]
    scenes = []
    for s in data["scenes"][: cfg["scenes"]]:
        n = clean(s["narration"])
        if n:
            scenes.append({"narration": n, "keywords": clean(s.get("keywords", "")) or "fitness"})
    data["scenes"] = scenes
    data["topic"] = topic
    return data
