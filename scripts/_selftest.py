"""اختبار محلي للمونتاج والترجمة العربية بدون إنترنت."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config, render, subs  # noqa: E402

FMT = sys.argv[1] if len(sys.argv) > 1 else "shorts"
W = config.WORK
W.mkdir(parents=True, exist_ok=True)
config.OUT.mkdir(exist_ok=True)

TEXTS = [
    "هل تريد حرق دهون البطن بسرعة؟",
    "ابدأ بتمرين البلانك لمدة ثلاثين ثانية يومياً",
    "ثم أضف عشرين تكرار من تمرين الضغط",
    "اشترك في القناة وزر موقع زمافيت",
]
PAT = ["testsrc2", "smptebars", "rgbtestsrc", "testsrc2"]

scenes = []
t = 0.0
for i, txt in enumerate(TEXTS):
    clip = W / f"clip_{i:02d}.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"{PAT[i]}=size=1920x1920:rate=30:duration=12",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    str(clip)], check=True)
    words = txt.split()
    dur = round(0.42 * len(words) + 0.7, 2)
    step = (dur - 0.5) / len(words)
    wl = [{"text": w, "start": round(0.25 + j * step, 2),
           "end": round(0.25 + (j + 1) * step - 0.03, 2)} for j, w in enumerate(words)]
    a = W / f"voice_{i:02d}.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"sine=frequency={220 + i * 40}:duration={dur}",
                    "-c:a", "libmp3lame", str(a)], check=True)
    scenes.append({"narration": txt, "keywords": "test", "clip": str(clip),
                   "clip_duration": 12, "audio": str(a), "duration": dur,
                   "words": wl, "start": t})
    t += dur

lst = W / "voices.txt"
lst.write_text("".join(f"file '{s['audio']}'\n" for s in scenes), encoding="utf-8")
vf = W / "voice.mp3"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                "-i", str(lst), "-c:a", "libmp3lame", str(vf)], check=True)

ass = subs.build(scenes, FMT, W / "subs.ass")
out = config.OUT / f"selftest_{FMT}.mp4"
render.build(scenes, FMT, ass, vf, t, W, out)
render.thumbnail(out, "احرق دهون البطن", FMT, W, config.OUT / f"selftest_{FMT}.jpg")
print("OK", out, f"{out.stat().st_size/1e6:.1f}MB", f"{t:.1f}s")
