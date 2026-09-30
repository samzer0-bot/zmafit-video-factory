"""إعدادات مصنع الفيديو — عدّل هنا فقط."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
WORK = OUT / "work"
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"
MUSIC = ASSETS / "music"

# ---------- الهوية ----------
# اللغة: ar (افتراضي) أو en — تُضبط من متغير البيئة VIDEO_LANG
CHANNEL_LANG = os.environ.get("VIDEO_LANG", "ar").strip().lower() or "ar"
if CHANNEL_LANG == "en":
    BRAND = "ZMAFIT"
    SITE = "zmafit.com"
else:
    BRAND = "Muscle Arabia"
    SITE = "zermixmusclearabia.com"

# ---------- المفاتيح (من GitHub Secrets) ----------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# ---------- الصوت ----------
# أصوات عربية مجانية من edge-tts. جرّب وغيّر حسب ذوقك:
#   ar-EG-ShakirNeural   (مصري، رجالي، حماسي)
#   ar-SA-HamedNeural    (فصيح، رجالي، هادئ)
#   ar-DZ-IsmaelNeural   (جزائري)
#   ar-EG-SalmaNeural    (مصري، نسائي)
_DEFAULT_VOICE = "en-US-AndrewNeural" if CHANNEL_LANG == "en" else "ar-EG-ShakirNeural"
_DEFAULT_RATE = "+5%" if CHANNEL_LANG == "en" else "+8%"
VOICE = os.environ.get("TTS_VOICE") or _DEFAULT_VOICE
VOICE_RATE = os.environ.get("TTS_RATE") or _DEFAULT_RATE     # سرعة الإلقاء
VOICE_PITCH = os.environ.get("TTS_PITCH", "+0Hz")

MUSIC_VOLUME_DB = -21          # مستوى الموسيقى الخلفية
VOICE_VOLUME_DB = 0

# ---------- الصيغ ----------
FORMATS = {
    "shorts": {
        "w": 1080, "h": 1920, "fps": 30,
        "target_seconds": 45,        # الهدف 30-60 ثانية
        "scenes": 6,
        "sub_fontsize": 74,
        "sub_margin_v": 420,
        "orientation": "portrait",
    },
    "long": {
        "w": 1920, "h": 1080, "fps": 30,
        "target_seconds": 240,       # 4 دقائق
        "scenes": 14,
        "sub_fontsize": 52,
        "sub_margin_v": 90,
        "orientation": "landscape",
    },
}

# ---------- ألوان الترجمة ----------
SUB_PRIMARY = "&H00FFFFFF"      # أبيض
SUB_HIGHLIGHT = "&H0000E5FF"    # أصفر/ذهبي (BGR)
SUB_OUTLINE = "&H00000000"      # أسود
SUB_FONT = "Cairo"

# ---------- يوتيوب ----------
# ابدأ بـ private حتى تتأكد من جودة أول فيديو، ثم غيّرها إلى public
YT_PRIVACY = os.environ.get("YT_PRIVACY", "private")
YT_CATEGORY = "17"          # 17 = رياضة | 26 = صحة وأسلوب حياة

# ---------- كلمات البحث الاحتياطية في Pexels ----------
FALLBACK_QUERIES = [
    "fitness workout", "gym training", "home workout",
    "running outdoor", "healthy food", "stretching exercise",
]
