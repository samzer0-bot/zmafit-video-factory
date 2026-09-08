"""بناء ملف ترجمة ASS عربي متزامن مع الصوت (كلمة بكلمة من edge-tts)."""
from pathlib import Path

import config

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{font},{size},{primary},{highlight},{outline},&H80000000,-1,0,0,0,100,100,0,0,1,{border},{shadow},2,60,60,{marginv},1
Style: Hook,{font},{hooksize},{highlight},{highlight},{outline},&H80000000,-1,0,0,0,100,100,0,0,1,{border},{shadow},5,60,60,0,1
Style: Brand,{font},{brandsize},&H4DFFFFFF,&H4DFFFFFF,{outline},&H80000000,-1,0,0,0,100,100,2,0,1,2,0,8,40,40,{brandmv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(t: float) -> str:
    if t < 0:
        t = 0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _chunks(words: list, max_words: int, max_chars: int):
    """يجمّع الكلمات في مجموعات قصيرة تُعرض معاً."""
    out, cur = [], []
    for w in words:
        cand = cur + [w]
        text = " ".join(x["text"] for x in cand)
        if cur and (len(cand) > max_words or len(text) > max_chars):
            out.append(cur)
            cur = [w]
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out


def build(scenes: list, fmt: str, out_path: Path) -> Path:
    cfg = config.FORMATS[fmt]
    portrait = cfg["orientation"] == "portrait"
    max_words = 4 if portrait else 7
    max_chars = 26 if portrait else 52

    lines = [HEADER.format(
        w=cfg["w"], h=cfg["h"], font=config.SUB_FONT,
        size=cfg["sub_fontsize"], hooksize=int(cfg["sub_fontsize"] * 1.25),
        primary=config.SUB_PRIMARY, highlight=config.SUB_HIGHLIGHT,
        outline=config.SUB_OUTLINE,
        border=5 if portrait else 3.5, shadow=2,
        marginv=cfg["sub_margin_v"],
        brandsize=int(cfg["h"] * 0.024),
        brandmv=int(cfg["h"] * 0.035),
    )]

    total = sum(s["duration"] for s in scenes) + 0.4
    lines.append(
        f"Dialogue: 0,{_ts(0)},{_ts(total)},Brand,,0,0,0,,{config.BRAND}"
    )

    for idx, sc in enumerate(scenes):
        base = sc["start"]
        words = sc.get("words") or []
        style = "Hook" if idx == 0 and portrait else "Main"

        if not words:
            # لا توجد توقيتات: اعرض نص المشهد كاملاً
            lines.append(
                f"Dialogue: 0,{_ts(base)},{_ts(base + sc['duration'])},{style},,0,0,0,,"
                f"{{\\fad(120,120)}}{sc['narration']}"
            )
            continue

        for grp in _chunks(words, max_words, max_chars):
            st = base + grp[0]["start"]
            en = base + grp[-1]["end"] + 0.12
            en = min(en, base + sc["duration"])
            if en <= st:
                continue
            text = " ".join(w["text"] for w in grp)
            lines.append(
                f"Dialogue: 0,{_ts(st)},{_ts(en)},{style},,0,0,0,,"
                f"{{\\fad(80,80)}}{text}"
            )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
