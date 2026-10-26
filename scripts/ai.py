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
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
]
SKIP_MODELS = ("gemini-2.5", "gemini-2.0", "gemini-1.5")   # لم تعد متاحة للحسابات الجديدة

_MODELS = None
RETRY_CODES = (429, 500, 502, 503, 504)
BACKOFF = [8, 20]


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

PROMPT_EN = """You are a scriptwriter for an English-language YouTube fitness channel called {brand}, focused on fat loss, home workouts and healthy habits.

Write a {kind} video script about this topic:
"{topic}"

STRICT RULES:
- Language: simple, energetic, conversational American English for a global audience.
- Scene 1 = a strong one-sentence hook that stops the scroll immediately.
- Exactly {n} scenes.
- Each scene: one or two short sentences, about {wps} words, because it will be read by a text-to-speech voice.
- The last scene = a call to subscribe and visit {site}.
- Absolutely forbidden: emojis, parentheses, asterisks, any formatting symbols. Clean spoken text only.
- No medical claims or cures. Safe general advice only.
- For every scene give "keywords": 2-4 English words describing a matching stock-footage shot (example: "man doing push ups gym").

Also provide:
- title: a catchy English YouTube title under 70 characters.
- description: 3 lines of English + one line with the link {site}.
- tags: 12 relevant English tags.
- thumbnail_text: 3 to 5 English words in capital letters for the thumbnail.
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
        and not m["name"].split("/")[-1].startswith(SKIP_MODELS)
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
    """يجرّب الموديلات؛ وإذا بقي الخادم مشغولاً يعيد الجولة بعد استراحة."""
    last = None
    for rnd in range(3):
        if rnd:
            print(f"  كل الموديلات مشغولة — جولة جديدة بعد 120s ({rnd + 1}/3)")
            time.sleep(120)
        try:
            return _ask_round(payload)
        except RuntimeError as e:
            last = e
    raise RuntimeError(f"فشل كل الموديلات. آخر خطأ: {last}")


def _ask_round(payload: dict) -> dict:
    last = None
    for model in models()[:4]:
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
    en = config.CHANNEL_LANG == "en"
    if en:
        kind = ("vertical short-form (YouTube Shorts) of about 45 seconds" if fmt == "shorts"
                else "horizontal video of about 5.5 minutes (at least 5 minutes)")
        wps = 15 if fmt == "shorts" else 30
    else:
        kind = "قصير عمودي (Shorts) مدته حوالي 45 ثانية" if fmt == "shorts" else "أفقي مدته حوالي 5.5 دقيقة (لا تقل عن 5 دقائق)"
        wps = 14 if fmt == "shorts" else 30

    prompt = (PROMPT_EN if en else PROMPT).format(
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

    # الفيديو الطويل: نتأكد أن عدد الكلمات يكفي (≈ 5 دقائق) ونعيد الطلب إن جاء قصيراً
    need = int(cfg["scenes"] * wps * 0.9) if fmt == "long" else 0
    best, best_words = None, -1
    for attempt in range(3):
        p = prompt
        if attempt:
            p += (f"\n\nIMPORTANT: your previous answer was too short ({best_words} words). "
                  f"Write at least {need} words of narration in total across exactly "
                  f"{cfg['scenes']} scenes, at least {wps - 4} words in EVERY scene. "
                  f"Add concrete examples, numbers and practical tips."
                  if en else
                  f"\n\nمهم: إجابتك السابقة قصيرة جداً ({best_words} كلمة). اكتب ما لا يقل عن {need} كلمة "
                  f"في مجموع السرد موزعة على {cfg['scenes']} مشهداً بالضبط، وكل مشهد لا يقل عن {wps - 4} كلمة. "
                  f"أضف أمثلة وأرقاماً ونصائح عملية.")
        payload["contents"] = [{"parts": [{"text": p}]}]
        raw = ask(payload)
        cand = json.loads(raw["candidates"][0]["content"]["parts"][0]["text"])
        words = sum(len(x.get("narration", "").split()) for x in cand.get("scenes", []))
        print(f"  عدد الكلمات: {words} (المطلوب ≥ {need})")
        if words > best_words:
            best, best_words = cand, words
        if words >= need:
            break
    data = best

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


def new_topic(recent: list) -> str:
    """يقترح موضوعاً جديداً عندما تفرغ قائمة المواضيع، مع تجنّب المواضيع الأخيرة."""
    en = config.CHANNEL_LANG == "en"
    avoid = "\n".join(f"- {t}" for t in recent[-60:]) or "-"
    if en:
        prompt = (f"Suggest ONE new topic for a short fitness video on the YouTube channel {config.BRAND} "
                  "(fat loss, home workouts, healthy habits). It must be clearly different from these "
                  f"recent topics:\n{avoid}\n\nReply with the topic only, one line, under 70 characters, "
                  "no quotes, no emojis.")
    else:
        prompt = (f"اقترح موضوعاً واحداً جديداً لفيديو لياقة قصير لقناة يوتيوب {config.BRAND} "
                  "(خسارة الدهون، تمارين منزلية، عادات صحية). يجب أن يختلف بوضوح عن هذه المواضيع الأخيرة:\n"
                  f"{avoid}\n\nأجب بالموضوع فقط في سطر واحد أقل من 70 حرفاً، بدون علامات تنصيص ولا رموز.")
    raw = ask({"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"temperature": 1.0}})
    text = raw["candidates"][0]["content"]["parts"][0]["text"]
    line = clean(text.strip().splitlines()[0]).strip(" \"'«»-.")
    return line[:90]
