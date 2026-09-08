"""توليد سكربت الفيديو بالعربية عبر Gemini (الباقة المجانية)."""
import json
import os
import re
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

_RESOLVED = None

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
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:600]
        raise RuntimeError(f"Gemini HTTP {e.code}: {body}") from None


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


def pick_model(available: list) -> str:
    """يختار موديلاً متاحاً يدعم generateContent."""
    usable = [
        m["name"].split("/")[-1] for m in available
        if "generateContent" in (m.get("supportedGenerationMethods") or [])
    ]
    if not usable:
        raise RuntimeError("لا يوجد أي موديل يدعم generateContent في هذا الحساب")

    for cand in MODEL_CANDIDATES:
        if cand and cand in usable:
            return cand

    usable.sort(key=lambda n: (_score(n), len(n)))
    if _score(usable[0]) >= 100:
        raise RuntimeError(f"لا يوجد موديل نصي مناسب. المتاح: {usable[:15]}")
    return usable[0]


def resolve_model() -> str:
    global _RESOLVED
    if _RESOLVED:
        return _RESOLVED
    data = _get(f"{BASE}/models?key={config.GEMINI_API_KEY}&pageSize=200")
    _RESOLVED = pick_model(data.get("models", []))
    print(f"  الموديل المستعمل: {_RESOLVED}")
    return _RESOLVED


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

    model = resolve_model()
    url = f"{BASE}/models/{model}:generateContent?key={config.GEMINI_API_KEY}"
    raw = _post(url, payload)
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
