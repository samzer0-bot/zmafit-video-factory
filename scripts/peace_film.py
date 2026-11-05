"""
"The Morning After" — a short documentary-style film about peace (English).

Real stock footage from Pexels (no AI imagery), a human-paced voice-over,
a cinematic grade (letterbox, film grain, crossfades) and a synthesized
ambient score: rumble and distant booms for the war half, a warm pad for
the peace half.

Usage:
    python scripts/peace_film.py            # needs PEXELS_API_KEY + internet
    python scripts/peace_film.py --dry-run  # offline test of the edit only
"""
import argparse
import asyncio
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

W, H, FPS = 1920, 1080, 24
BAR = 138                      # letterbox bars -> ~2.39:1 picture
XF = 0.9                       # crossfade length (seconds)
VOICES = ["en-US-AndrewMultilingualNeural", "en-US-AndrewNeural",
          "en-GB-RyanNeural"]
RATE, PITCH = "-7%", "-2Hz"

TITLE = "The Morning After"

# mood: war / turn / peace.  pre/post = silence around the line (seconds).
SCENES = [
    {"mood": "war", "pre": 1.6, "post": 0.9,
     "q": ["city street morning", "city traffic morning"],
     "text": "Nobody wakes up thinking it's the last ordinary morning."},
    {"mood": "war", "pre": 0.4, "post": 1.2,
     "q": ["explosion smoke", "explosion", "black smoke"],
     "text": "Then the windows shake. And the street you grew up on... stops being a street."},
    {"mood": "war", "pre": 0.3, "post": 0.8,
     "q": ["soldiers walking", "soldier", "military"],
     "text": "War doesn't ask your name. It doesn't care what you had planned for the weekend."},
    {"mood": "war", "pre": 0.3, "post": 0.9,
     "q": ["destroyed building", "ruins", "abandoned building rubble"],
     "text": "It takes the bakery. The school. The bench where your father used to sit."},
    {"mood": "war", "pre": 0.3, "post": 0.9,
     "q": ["fire burning night", "fire", "burning"],
     "text": "People carry whatever fits in two hands. Everything else stays behind."},
    {"mood": "war", "pre": 0.3, "post": 1.4,
     "q": ["sad child window", "child looking out window", "lonely child"],
     "text": "And somewhere, a kid learns the difference between thunder... and something worse."},
    {"mood": "war", "pre": 0.3, "post": 1.6,
     "q": ["smoke over city aerial", "smoke aerial", "dust storm"],
     "text": "We've been doing this for thousands of years. And every time, we tell ourselves it's the last time."},
    {"mood": "turn", "pre": 1.8, "post": 0.8,
     "q": ["sunrise over city", "sunrise", "sun rays clouds"],
     "text": "But there's a part they never show on the news."},
    {"mood": "peace", "pre": 0.3, "post": 0.8,
     "q": ["construction worker bricks", "building construction hands", "rebuilding"],
     "text": "The morning after, someone picks up the first brick."},
    {"mood": "peace", "pre": 0.3, "post": 0.8,
     "q": ["sharing bread", "people sharing food", "family dinner table"],
     "text": "Someone shares their bread with a stranger. Someone opens a door."},
    {"mood": "peace", "pre": 0.3, "post": 1.0,
     "q": ["children playing football street", "kids playing outside", "children running field"],
     "text": "Kids find a ball, a wall... and a reason to laugh again."},
    {"mood": "peace", "pre": 0.4, "post": 1.0,
     "q": ["holding hands", "hands together", "hug"],
     "text": "Peace isn't a speech. It isn't a flag. It's small, and it's slow, "
             "and it gets chosen, again and again, by ordinary people."},
    {"mood": "peace", "pre": 0.4, "post": 4.5,
     "q": ["white dove flying", "birds flying sunset", "birds flying sky"],
     "text": "Maybe it's the bravest thing we ever do."},
]

GRADE = {
    # cold, desaturated, crushed — war
    "war": "eq=contrast=1.16:saturation=0.45:brightness=-0.035:gamma=0.95,"
           "colorbalance=bs=0.07:bm=0.03:rh=-0.03",
    # neutral, first light
    "turn": "eq=contrast=1.08:saturation=0.75:brightness=-0.01,"
            "colorbalance=rh=0.03:bh=-0.02",
    # warm, soft — peace
    "peace": "eq=contrast=1.05:saturation=0.92:gamma=1.02,"
             "colorbalance=rs=0.04:rm=0.035:bh=-0.04",
}


# ---------------------------------------------------------------- helpers
def run(args, desc=""):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        print("CMD:", " ".join(shlex.quote(a) for a in args)[:3000])
        print(p.stderr[-4000:])
        raise RuntimeError(f"ffmpeg failed: {desc}")
    return p


def probe(path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


# ---------------------------------------------------------------- footage
def fetch_footage(work: Path, dry: bool):
    if dry:
        colors = {"war": "0x3a3f45", "turn": "0x8a7a60", "peace": "0xc9a46a"}
        for i, sc in enumerate(SCENES):
            dest = work / f"clip_{i:02d}.mp4"
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                 "testsrc2=s=1280x720:r=24:d=12",
                 "-f", "lavfi", "-i", f"color=c={colors[sc['mood']]}:s=1280x720:d=12",
                 "-filter_complex", "[0][1]blend=all_mode=overlay", "-t", "12",
                 "-c:v", "libx264", "-preset", "ultrafast", str(dest)], "dummy clip")
            sc["clip"], sc["clip_dur"] = str(dest), 12.0
        return

    import stock  # reuse the factory's Pexels client
    if not (config.PEXELS_API_KEY or "").strip():
        raise SystemExit("PEXELS_API_KEY is missing")
    used = set()
    for i, sc in enumerate(SCENES):
        chosen = None
        for q in sc["q"]:
            for orient, min_side in (("landscape", 1920), ("landscape", 1280), (None, 1280)):
                chosen = stock._search(q, orient, False, used, min_side)
                if chosen:
                    break
            if chosen:
                break
        if not chosen:
            raise RuntimeError(f"no footage for scene {i}: {sc['q']}")
        _, link, vid, dur = chosen
        used.add(vid)
        dest = work / f"clip_{i:02d}.mp4"
        stock._download(link, dest)
        sc["clip"], sc["clip_dur"], sc["pexels_id"] = str(dest), float(dur or 10), vid
        print(f"  ✓ scene {i + 1:02d}: pexels#{vid} '{q}'")


# ---------------------------------------------------------------- voice
async def _tts(text, voice, out):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=RATE, pitch=PITCH)
    await comm.save(str(out))


def narrate(work: Path, dry: bool):
    for i, sc in enumerate(SCENES):
        raw = work / f"vo_raw_{i:02d}.mp3"
        if dry:
            secs = max(2.0, len(sc["text"]) / 15)
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                 f"sine=f=180:d={secs:.2f}", str(raw)], "dummy vo")
        else:
            ok = False
            for voice in VOICES:
                for _ in range(3):
                    try:
                        asyncio.run(_tts(sc["text"], voice, raw))
                        if raw.exists() and raw.stat().st_size > 1500:
                            ok = True
                            break
                    except Exception as e:  # noqa: BLE001
                        print(f"  ! tts {voice}: {e}")
                if ok:
                    break
            if not ok:
                from gtts import gTTS
                gTTS(sc["text"], lang="en", tld="co.uk", slow=False).save(str(raw))
        # trim the synth's leading/trailing silence so our own pauses rule
        clean = work / f"vo_{i:02d}.wav"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af",
             "silenceremove=start_periods=1:start_threshold=-50dB,"
             "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse",
             "-ar", "48000", "-ac", "1", str(clean)], "vo trim")
        sc["vo"], sc["vo_dur"] = str(clean), probe(clean)
        sc["dur"] = sc["pre"] + sc["vo_dur"] + sc["post"] + XF
        print(f"  ✓ vo {i + 1:02d}: {sc['vo_dur']:.1f}s")


# ---------------------------------------------------------------- picture
def segment(i, sc, work: Path) -> Path:
    out = work / f"seg_{i:02d}.mp4"
    d = sc["dur"]
    src = sc.get("clip_dur", 10)
    start = 0.0
    if src > d + 1.5:
        start = min(2.0, (src - d) / 3)
    # slow-motion stretch if the clip is too short instead of a visible loop
    slow = ""
    if src < d - 0.2:
        factor = min(2.0, (d + 0.3) / max(src - start, 1.0))
        slow = f"setpts={factor:.3f}*PTS,"
    vf = (
        f"{slow}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"fps={FPS},{GRADE[sc['mood']]},"
        f"noise=alls=9:allf=t,vignette=PI/4.6,"
        f"drawbox=x=0:y=0:w=iw:h={BAR}:color=black:t=fill,"
        f"drawbox=x=0:y=ih-{BAR}:w=iw:h={BAR}:color=black:t=fill,"
        f"format=yuv420p"
    )
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}",
         "-stream_loop", "-1", "-i", sc["clip"], "-t", f"{d:.3f}", "-an",
         "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "17", str(out)], f"segment {i}")
    return out


def picture(work: Path) -> tuple[Path, float]:
    segs = [segment(i, sc, work) for i, sc in enumerate(SCENES)]
    t = 0.0
    for sc in SCENES:              # start time of each scene on the timeline
        sc["t0"] = t
        t += sc["dur"] - XF
    total = t + XF

    inputs, chain, last = [], [], "[0:v]"
    for p in segs:
        inputs += ["-i", str(p)]
    for i in range(1, len(segs)):
        off = SCENES[i]["t0"]
        # the war -> dawn cut is a slow dip through black
        tr = "fadeblack" if SCENES[i]["mood"] == "turn" else "fade"
        dur = 1.6 if tr == "fadeblack" else XF
        if dur > XF:
            off -= (dur - XF)
        lbl = f"[x{i}]"
        chain.append(f"{last}[{i}:v]xfade=transition={tr}:duration={dur}:offset={off:.3f}{lbl}")
        last = lbl
    chain.append(f"{last}fade=t=in:st=0:d=1.5,fade=t=out:st={total - 2.5:.3f}:d=2.5[v]")
    out = work / "picture.mp4"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(chain),
         "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
         "-pix_fmt", "yuv420p", str(out)], "xfade chain")
    return out, total


# ---------------------------------------------------------------- sound
def score(work: Path, total: float) -> Path:
    turn = next(sc["t0"] for sc in SCENES if sc["mood"] == "turn")
    T = f"{total:.3f}"
    # war bed: low rumble + slow minor drone
    rumble = (f"anoisesrc=c=brown:a=0.5:d={T}:r=48000,lowpass=f=110,lowpass=f=110,"
              f"volume=0.55,tremolo=f=0.13:d=0.6,"
              f"afade=t=in:d=4,afade=t=out:st={turn - 1:.2f}:d=3")
    drone_minor = (f"sine=f=55:d={T}:r=48000[a0];sine=f=65.41:d={T}:r=48000[a1];"
                   f"sine=f=82.41:d={T}:r=48000[a2];"
                   f"[a0][a1][a2]amix=inputs=3,volume=0.5,tremolo=f=0.2:d=0.3,"
                   f"afade=t=in:d=6,afade=t=out:st={turn - 1.5:.2f}:d=3")
    # warm major pad for the peace half (slightly detuned pairs = chorus)
    notes = [110, 110.6, 164.81, 220, 220.9, 277.18, 329.63]
    pad_in = ";".join(f"sine=f={f}:d={T}:r=48000[p{k}]" for k, f in enumerate(notes))
    pad = (f"{pad_in};{''.join(f'[p{k}]' for k in range(len(notes)))}"
           f"amix=inputs={len(notes)},volume=0.9,lowpass=f=900,tremolo=f=0.25:d=0.25,"
           f"aecho=0.8:0.7:120|260:0.3|0.2,"
           f"afade=t=in:st=0:d=0.01,volume=0:enable='lt(t,{turn:.2f})',"
           f"afade=t=in:st={turn:.2f}:d=7,afade=t=out:st={total - 5:.2f}:d=5")
    # distant booms during the war half
    booms = []
    for k, sc in enumerate(SCENES[1:6], start=1):
        at = sc["t0"] + 0.25 + (k % 2) * 1.7
        booms.append(
            f"anoisesrc=c=brown:a=1:d=3.5:r=48000,lowpass=f={90 + 12 * k},"
            f"afade=t=in:d=0.03,afade=t=out:st=0.05:d=3.4,"
            f"volume={1.6 if k == 1 else 0.9},adelay={int(at * 1000)}:all=1,"
            f"apad=whole_dur={T}[b{k}]")
    g = (f"{rumble}[r];{drone_minor}[dm];{pad}[pd];" + ";".join(booms) + ";"
         f"[r][dm][pd]{''.join(f'[b{k}]' for k in range(1, len(booms) + 1))}"
         f"amix=inputs={3 + len(booms)}:normalize=0,"
         f"atrim=0:{T},volume=0.35,alimiter=limit=0.7[m]")
    out = work / "score.wav"
    run(["ffmpeg", "-y", "-v", "error", "-filter_complex", g, "-map", "[m]",
         "-ac", "2", "-ar", "48000", str(out)], "score")
    return out


def voice_track(work: Path, total: float) -> Path:
    inputs, parts = [], []
    for i, sc in enumerate(SCENES):
        inputs += ["-i", sc["vo"]]
        at = int((sc["t0"] + sc["pre"]) * 1000)
        parts.append(f"[{i}:a]adelay={at}:all=1,apad=whole_dur={total:.3f}[v{i}]")
    g = (";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(len(SCENES))) +
         f"amix=inputs={len(SCENES)}:normalize=0,atrim=0:{total:.3f},"
         # make the synth sound recorded: warm EQ, gentle comp, small room
         "highpass=f=75,lowpass=f=11500,"
         "equalizer=f=180:t=q:w=1:g=2.5,equalizer=f=3200:t=q:w=1.2:g=-1.5,"
         "acompressor=threshold=-20dB:ratio=3:attack=8:release=180,"
         "aecho=0.85:0.9:28|47:0.10|0.06[vo]")
    out = work / "voice.wav"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", g,
         "-map", "[vo]", "-ac", "2", "-ar", "48000", str(out)], "voice track")
    return out


# ---------------------------------------------------------------- captions
def ass_time(t):
    t = max(0.0, t)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def captions(work: Path, total: float) -> Path:
    lines = []
    for sc in SCENES:
        start = sc["t0"] + sc["pre"]
        chunks = [c.strip() for c in re.split(r"(?<=[.?!])\s+", sc["text"]) if c.strip()]
        n = sum(len(c) for c in chunks)
        t = start
        for c in chunks:
            d = sc["vo_dur"] * len(c) / n
            lines.append(f"Dialogue: 0,{ass_time(t)},{ass_time(t + d + 0.25)},Sub,,0,0,0,,"
                         f"{{\\fad(150,150)}}{c}")
            t += d
    end_t = total - 4.2
    lines.append(f"Dialogue: 1,{ass_time(end_t)},{ass_time(total)},End,,0,0,0,,"
                 f"{{\\fad(900,600)}}Choose peace.")
    ass = work / "film.ass"
    ass.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,DejaVu Serif,40,&H00EAEAEA,&H00EAEAEA,&H00000000,&H00000000,0,0,0,0,100,100,0.5,0,1,1.2,0,2,160,160,44,1
Style: End,DejaVu Serif,74,&H00F2F2F2,&H00F2F2F2,&H00000000,&H90000000,0,0,0,0,100,100,6,0,1,0,3,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(lines) + "\n", encoding="utf-8")
    return ass


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    out_dir = config.OUT
    work = out_dir / "peace_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    print("• footage"); fetch_footage(work, a.dry_run)
    print("• voice-over"); narrate(work, a.dry_run)
    print("• picture"); pic, total = picture(work)
    print(f"  timeline {total:.1f}s")
    print("• sound"); mus = score(work, total); vo = voice_track(work, total)
    ass = captions(work, total)

    final = out_dir / "the_morning_after.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(pic), "-i", str(vo), "-i", str(mus),
         "-filter_complex",
         "[2:a]volume=1.0[m];[1:a]asplit=2[v][sc];"
         "[m][sc]sidechaincompress=threshold=0.04:ratio=4:attack=30:release=500[md];"
         "[v][md]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]",
         "-map", "0:v", "-map", "[a]",
         "-vf", f"subtitles={shlex.quote(str(ass))}",
         "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "9M", "-bufsize", "18M",
         "-tune", "grain", "-profile:v", "high",
         "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", str(final)], "final")

    thumb = out_dir / "the_morning_after.jpg"
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{SCENES[3]['t0'] + 2:.2f}", "-i", str(pic),
         "-frames:v", "1", "-q:v", "2", str(thumb)], "thumb")

    meta = {
        "title": "The Morning After — A Short Film About Peace",
        "description": "\n".join(sc["text"] for sc in SCENES) +
                       "\n\nChoose peace.\n\nFootage: Pexels (free license).",
        "tags": ["peace", "war", "short film", "humanity", "hope", "documentary"],
        "duration": round(total, 1),
        "clips": [{"pexels_id": sc.get("pexels_id"), "query": sc["q"][0]} for sc in SCENES],
    }
    (out_dir / "the_morning_after.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ done: {final} ({final.stat().st_size // 1024 // 1024}MB, {total:.1f}s)")


if __name__ == "__main__":
    main()
