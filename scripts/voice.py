"""التعليق الصوتي العربي عبر edge-tts (مجاني بالكامل، بدون مفتاح API)."""
import asyncio
import subprocess
from pathlib import Path

import edge_tts

import config


async def _speak(text: str, out_mp3: Path):
    """ينطق النص ويعيد قائمة توقيتات الكلمات بالثواني."""
    comm = edge_tts.Communicate(
        text, config.VOICE, rate=config.VOICE_RATE, pitch=config.VOICE_PITCH
    )
    words = []
    with open(out_mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 1e7,
                    "end": (chunk["offset"] + chunk["duration"]) / 1e7,
                })
    return words


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def narrate(scenes: list, workdir: Path) -> list:
    """ينتج ملف صوت لكل مشهد ويضيف المدة وتوقيت الكلمات."""
    workdir.mkdir(parents=True, exist_ok=True)
    result = []
    for i, sc in enumerate(scenes):
        mp3 = workdir / f"voice_{i:02d}.mp3"
        for attempt in range(3):
            try:
                words = asyncio.run(_speak(sc["narration"], mp3))
                if mp3.exists() and mp3.stat().st_size > 800:
                    break
            except Exception as e:                       # noqa: BLE001
                print(f"  ! محاولة {attempt + 1} فشلت للمشهد {i}: {e}")
                words = []
        else:
            raise RuntimeError(f"تعذّر توليد صوت المشهد {i}")

        d = duration(mp3)
        result.append({**sc, "audio": str(mp3), "duration": d, "words": words})
        print(f"  ✓ مشهد {i + 1}: {d:.1f}s — {sc['narration'][:45]}")
    return result


def concat_audio(scenes: list, out_path: Path) -> float:
    """يدمج أصوات المشاهد في ملف واحد ويضبط بداية كل مشهد."""
    lst = out_path.parent / "voices.txt"
    lst.write_text("".join(f"file '{s['audio']}'\n" for s in scenes), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c:a", "libmp3lame", "-b:a", "192k", str(out_path)],
        check=True,
    )
    t = 0.0
    for s in scenes:
        s["start"] = t
        t += s["duration"]
    return t
