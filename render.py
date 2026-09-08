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
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
        "-r", str(fps), "-g", str(fps * 2),
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart", str(out_file),
    ]
    print("• الترميز النهائي…")
    run(args, "final render")
    return out_file


def thumbnail(video: Path, text: str, fmt: str, workdir: Path, out_file: Path) -> Path:
    """صورة مصغرة: إطار نظيف (قبل الترجمة) + نص عربي مُشكَّل عبر libass."""
    cfg = config.FORMATS[fmt]
    base = workdir / "base.mp4"
    if base.exists():
        video = base
    tw, th = 1280, 720          # مقاس يوتيوب القياسي للصور المصغرة
    size = int(th * 0.105)

    ass = workdir / "thumb.ass"
    ass.write_text(
        f"""[Script Info]
ScriptType: v4.00+
PlayResX: {tw}
PlayResY: {th}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,{config.SUB_FONT},{size},{config.SUB_HIGHLIGHT},{config.SUB_HIGHLIGHT},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:10.00,T,,0,0,0,,{text}
""", encoding="utf-8")

    try:
        d = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(video)],
            capture_output=True, text=True, check=True).stdout.strip())
        seek = max(1.0, d * 0.28)
    except Exception:                                    # noqa: BLE001
        seek = 1.2

    run([
        "ffmpeg", "-y", "-v", "error", "-ss", f"{seek:.2f}", "-i", str(video),
        "-vf", (f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},"
                f"eq=contrast=1.12:saturation=1.2:brightness=-0.03,"
                f"subtitles={shlex.quote(str(ass))}:fontsdir={shlex.quote(str(config.FONTS))}"),
        "-frames:v", "1", "-q:v", "2", str(out_file),
    ], "thumbnail")
    return out_file
