"""المونتاج النهائي بـ ffmpeg — مجاني بالكامل."""
import random
import shlex
import subprocess
from pathlib import Path

import config


def run(args: list, desc: str = ""):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        print("FFMPEG CMD:", " ".join(shlex.quote(a) for a in args)[:2000])
        print(p.stderr[-4000:])
        raise RuntimeError(f"فشل ffmpeg: {desc}")
    return p


def _segment(scene: dict, idx: int, cfg: dict, workdir: Path) -> Path:
    """يحوّل لقطة المشهد إلى مقطع صامت بالمقاس والمدة المطلوبين."""
    w, h, fps = cfg["w"], cfg["h"], cfg["fps"]
    dur = scene["duration"] + 0.25          # هامش صغير
    out = workdir / f"seg_{idx:02d}.mp4"

    # نقطة بداية عشوائية داخل اللقطة لتفادي التكرار الممل
    src_dur = scene.get("clip_duration") or 10
    start = 0.0
    if src_dur > dur + 2:
        start = round(random.uniform(0, min(3.0, src_dur - dur - 1)), 2)

    zoom_dir = 1 if idx % 2 == 0 else -1
    if zoom_dir == 1:
        zexpr = f"min(1.0+0.0009*on,1.14)"
    else:
        zexpr = f"max(1.14-0.0009*on,1.0)"

    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d=1:s={w}x{h}:fps={fps},"
        f"eq=contrast=1.06:saturation=1.12,"
        f"format=yuv420p"
    )

    run([
        "ffmpeg", "-y", "-v", "error",
        "-ss", str(start), "-stream_loop", "-1", "-i", scene["clip"],
        "-t", f"{dur:.3f}", "-an",
        "-vf", vf, "-r", str(fps),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", str(out),
    ], f"segment {idx}")
    return out


def _pick_music() -> Path | None:
    if not config.MUSIC.exists():
        return None
    tracks = sorted([p for p in config.MUSIC.iterdir()
                     if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg")])
    return random.choice(tracks) if tracks else None


def build(scenes: list, fmt: str, ass_file: Path, voice_file: Path,
          total: float, workdir: Path, out_file: Path) -> Path:
    cfg = config.FORMATS[fmt]
    w, h, fps = cfg["w"], cfg["h"], cfg["fps"]

    print("• تجهيز المشاهد…")
    segs = [_segment(sc, i, cfg, workdir) for i, sc in enumerate(scenes)]

    lst = workdir / "segments.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segs), encoding="utf-8")
    base = workdir / "base.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(base)], "concat")

    music = _pick_music()
    fontsdir = str(config.FONTS)

    # العلامة المائية والترجمة كلاهما عبر libass (تشكيل عربي صحيح)
    vf = (
        f"subtitles={shlex.quote(str(ass_file))}:fontsdir={shlex.quote(fontsdir)},"
        f"vignette=PI/5"
    )

    args = ["ffmpeg", "-y", "-v", "error", "-i", str(base), "-i", str(voice_file)]
    if music:
        args += ["-stream_loop", "-1", "-i", str(music)]
        af = (
            f"[1:a]volume={config.VOICE_VOLUME_DB}dB,asplit=2[v1][vsc];"
            f"[2:a]volume={config.MUSIC_VOLUME_DB}dB,afade=t=out:st={max(total-2,0):.2f}:d=2[m0];"
            f"[m0][vsc]sidechaincompress=threshold=0.05:ratio=6:attack=15:release=350[m1];"
            f"[v1][m1]amix=inputs=2:duration=first:dropout_transition=0[aout]"
        )
        args += ["-filter_complex", af, "-map", "0:v", "-map", "[aout]"]
    else:
        args += ["-map", "0:v", "-map", "1:a"]

    args += [
        "-vf", vf,
        "-t", f"{total + 0.4:.3f}",
        *(["-c:v", "libx264", "-preset", "medium", "-crf", "20"] if fmt != "long" else
          # الفيديو الطويل: سقف للحجم (< ~90MB) لأن Make يرفض تنزيل الملفات الأكبر من ~100MB
          ["-c:v", "libx264", "-preset", "faster", "-crf", "23",
           "-maxrate", "1600k", "-bufsize", "3200k"]),
        "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
        "-r", str(fps), "-g", str(fps * 2),
        "-c:a", "aac", "-b:a", "192k" if fmt != "long" else "128k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart", str(out_file),
    ]
    print("• الترميز النهائي…")
    run(args, "final render")
    return out_file


def _best_frame(video: Path, workdir: Path) -> Path:
    """يختار أكثر إطار مضيء وملوّن من عدة نقاط في الفيديو (بدل إطار عشوائي مظلم)."""
    try:
        d = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(video)],
            capture_output=True, text=True, check=True).stdout.strip())
    except Exception:                                    # noqa: BLE001
        d = 10.0
    best, best_score = None, -1e9
    for i, frac in enumerate([0.06, 0.15, 0.24, 0.33, 0.42, 0.52, 0.62, 0.72]):
        f = workdir / f"cand_{i}.png"
        p = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.5, d * frac):.2f}", "-i", str(video),
             "-frames:v", "1", "-vf", "scale=640:-2", str(f)], capture_output=True, text=True)
        if p.returncode != 0 or not f.exists():
            continue
        st = subprocess.run(
            ["ffprobe", "-v", "error", "-f", "lavfi", "-i",
             f"movie={f},signalstats", "-show_entries",
             "frame_tags=lavfi.signalstats.YAVG,lavfi.signalstats.SATAVG",
             "-of", "default=nw=1"], capture_output=True, text=True).stdout
        vals = dict(l.split("=", 1) for l in st.splitlines() if "=" in l)
        y = float(vals.get("TAG:lavfi.signalstats.YAVG", 0) or 0)
        sat = float(vals.get("TAG:lavfi.signalstats.SATAVG", 0) or 0)
        score = -abs(y - 120) + sat * 0.8          # مضيء بدون احتراق + ألوان
        if score > best_score:
            best, best_score = f, score
    return best or video


def _ass_escape(t: str) -> str:
    return t.replace("\\", " ").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def _fit(text: str, size: int, max_w: int, min_size: int) -> int:
    """يصغّر الخط حتى يتسع السطر للعرض المتاح (تقدير تقريبي لعرض خط Cairo العريض)."""
    est = lambda s: len(text) * s * (0.62 if text.isascii() else 0.40)   # noqa: E731
    while size > min_size and est(size) > max_w:
        size -= 4
    return size


def _split2(text: str, size: int, max_w: int) -> list:
    """يقسم النص لسطرين إذا كان سيصغر كثيراً في سطر واحد."""
    words = text.split()
    if len(words) < 2 or _fit(text, size, max_w, 10) >= size * 0.85:
        return [text] if text else []
    mid = (len(words) + 1) // 2
    return [" ".join(words[:mid]), " ".join(words[mid:])]


def thumbnail(video: Path, text: str, fmt: str, workdir: Path, out_file: Path,
              parts: dict = None, photo: Path = None) -> Path:
    """صورة مصغرة بأسلوب القناة: صورة مضيئة + تدرج داكن + كلمة ضخمة صفراء + نص أبيض + شريط أبيض."""
    parts = parts or {}
    en = config.CHANNEL_LANG == "en"
    tw, th = 1280, 720

    hook = _ass_escape(parts.get("thumb_hook") or "")
    main = _ass_escape(parts.get("thumb_main") or "")
    tag = _ass_escape(parts.get("thumb_tag") or "")
    if not hook and not main:                         # احتياطي: النص القديم
        words = _ass_escape(text).split()
        hook, main = " ".join(words[:1]), " ".join(words[1:])
    if en:
        hook, main, tag = hook.upper(), main.upper(), tag.upper()

    src = photo if (photo and Path(photo).exists()) else None
    if src is None:
        base = workdir / "base.mp4"
        src = _best_frame(base if base.exists() else video, workdir)

    # النص على اليمين للعربية، على اليسار للإنجليزية
    right = not en
    an = 6 if right else 4
    x = tw - 60 if right else 60
    max_w = 700

    hs = _fit(hook, 200, max_w, 100) if hook else 0
    main_lines = _split2(main, 120, max_w)
    ms = min(_fit(l, 120, max_w, 64) for l in main_lines) if main_lines else 0
    ts = 66

    # توزيع عمودي
    blocks = []
    if hook:
        blocks.append(("H", hook, int(hs * 0.98)))
    for l in main_lines:
        blocks.append(("M", l, int(ms * 0.86)))
    if tag:
        blocks.append(("T", tag, int(ts * 1.75)))
    total = sum(b[2] for b in blocks)
    y = (th - total) // 2
    events = []
    for kind, t, hgt in blocks:
        cy = y + hgt // 2
        events.append(f"Dialogue: 0,0:00:00.00,0:00:10.00,{kind},,0,0,0,,{{\\an{an}\\pos({x},{cy})}}{t}")
        y += hgt
    brand = config.BRAND.upper()
    bx = 40 if right else tw - 40
    events.append(f"Dialogue: 0,0:00:00.00,0:00:10.00,B,,0,0,0,,{{\\an{7 if right else 9}\\pos({bx},30)}}{brand}")

    F = config.SUB_FONT
    FB = "Cairo Black" if (config.FONTS / "Cairo-Black.ttf").exists() else F
    ass = workdir / "thumb.ass"
    ass.write_text(
        f"""[Script Info]
ScriptType: v4.00+
PlayResX: {tw}
PlayResY: {th}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: H,{FB},{hs or 100},&H0000D7FF,&H0000D7FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,7,5,5,0,0,0,1
Style: M,{FB},{ms or 80},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,6,4,5,0,0,0,1
Style: T,{F},{ts},&H00101010,&H00101010,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,3,14,0,5,0,0,0,1
Style: B,{F},34,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,2,0,1,3,2,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n", encoding="utf-8")

    # تدرج داكن خلف النص فقط (الجهة الأخرى تبقى مضيئة)
    grad = (f"(X-{tw*0.30:.0f})/{tw*0.45:.0f}" if right else f"({tw*0.70:.0f}-X)/{tw*0.45:.0f}")
    fc = (
        f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},"
        f"eq=contrast=1.15:saturation=1.35:brightness=0.03,unsharp=5:5:0.8,format=rgba[bg];"
        f"color=c=black:s={tw}x{th}:d=1,format=rgba,"
        f"geq=r='8':g='14':b='20':a='clip(235*{grad},0,225)'[sh];"
        f"[bg][sh]overlay=format=auto,"
        f"drawbox=x={tw - 14 if right else 0}:y=0:w=14:h={th}:color=0xFFD700@1:t=fill,"
        f"format=yuv420p,"
        f"subtitles={shlex.quote(str(ass))}:fontsdir={shlex.quote(str(config.FONTS))}[out]"
    )
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-filter_complex", fc,
         "-map", "[out]", "-frames:v", "1", "-q:v", "2", str(out_file)], "thumbnail")
    return out_file
