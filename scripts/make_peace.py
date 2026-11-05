"""
"Make Peace" — a ~5 minute documentary-style school film (English).

Structure
  Opening   : the students' "make peace" title card
  Part One  : how wars begin (causes, WWI, WWII)
  Part Two  : a world still at war
  Part Three: hope
  Part Four : building peace (five solutions)
  Ending    : "Let's make peace." + title card again

Visuals: the students' own images (assets/make_peace) with a slow
Ken-Burns move over a blurred backdrop, mixed with real Pexels footage.
Sound : edge-tts voice-over treated to sound recorded, synthesized score.

    python scripts/make_peace.py            # needs PEXELS_API_KEY + internet
    python scripts/make_peace.py --dry-run  # offline test of the edit only
"""
import argparse
import asyncio
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

DRY_SMALL = os.environ.get("MP_SMALL") == "1"
W, H = (960, 540) if DRY_SMALL else (1920, 1080)
FPS = 24
BAR = round(H * 0.128)          # letterbox bars -> ~2.39:1 picture
INNER = H - 2 * BAR
XF = 0.9                        # crossfade (s)
VOICES = ["en-US-AndrewMultilingualNeural", "en-US-AndrewNeural", "en-GB-RyanNeural"]
RATE, PITCH = "-10%", "-4Hz"
IMG = config.ASSETS / "make_peace"
SERIF = "EB Garamond"

GRADE = {
    "war": "eq=contrast=1.14:saturation=0.55:brightness=-0.03:gamma=0.96,"
           "colorbalance=bs=0.06:bm=0.03:rh=-0.02",
    "img": "eq=contrast=1.05:saturation=0.95",
    # archival newsreel look: B&W, warm tint, flicker, heavy grain
    "archive": "hue=s=0,eq=contrast=1.28:brightness='-0.03+0.025*sin(t*31)':eval=frame,"
               "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,"
               "eq=saturation=0.35,noise=alls=24:allf=t",
    "turn": "eq=contrast=1.08:saturation=0.8:brightness=-0.01,colorbalance=rh=0.03:bh=-0.02",
    "peace": "eq=contrast=1.05:saturation=0.95:gamma=1.02,"
             "colorbalance=rs=0.04:rm=0.03:bh=-0.04",
}


def S(kind, text="", mood="war", pre=0.4, post=0.9, **kw):
    return {"kind": kind, "text": text, "mood": mood, "pre": pre, "post": post, **kw}


def card(num, title, mood):
    return S("card", mood=mood, num=num, title=title, hold=4.6)


SCENES = [
    # ------------------------------------------------------------ opening
    S("title", "This is a story about war... and about the people who refuse "
      "to let war have the last word.", mood="title", pre=4.0, post=2.2,
      img="00_title.jpg"),

    # ------------------------------------------------------------ part one
    card("PART ONE", "How Wars Begin", "war"),
    S("clip", "No war starts with the first shot. It starts long before that: in fear, "
      "in anger, and in the belief that the other side is less human than we are.",
      q=["storm clouds dark", "dark clouds timelapse"]),
    S("clip", "Some wars begin over land, water or oil. When resources are scarce, "
      "neighbours become rivals.",
      q=["oil field pump", "desert land aerial", "dry cracked earth"], tag="Land & Resources"),
    S("clip", "Some begin over power: a leader who wants more, or a government that "
      "refuses to share it.",
      q=["parliament building", "government building columns", "chess pieces"], tag="Power"),
    S("clip", "Others grow from old wounds. Differences of religion, ethnicity or language "
      "are turned into weapons by people who profit from hate.",
      q=["crowd silhouette", "broken glass", "shadows people walking"], tag="Hate & Division"),
    S("clip", "Poverty and injustice feed them too. When people feel they have nothing "
      "left to lose, violence starts to look like an answer.",
      q=["empty plate", "abandoned house interior", "old worn shoes"], tag="Poverty & Injustice"),
    S("clip", "History shows how small the spark can be. In nineteen fourteen, one "
      "assassination in Sarajevo pulled the great powers of Europe into the First World War.",
      q=["old steam train", "vintage pocket watch", "old city street black and white"], mood="archive",
      loc="SARAJEVO, BOSNIA  —  28 JUNE 1914"),
    S("img", "In nineteen thirty-nine, the invasion of Poland began the Second World War. "
      "By the time it ended, more than seventy million people were dead.",
      img="02_battle_planes.jpg", mood="archive", loc="POLAND  —  1 SEPTEMBER 1939", post=1.2),
    S("img", "Behind every number, there is a person. Someone's son. Someone's daughter.",
      img="01_soldier_child.jpg", post=2.0),

    # ------------------------------------------------------------ part two
    card("PART TWO", "A World Still at War", "war"),
    S("clip", "You might think those days are behind us. They are not.",
      q=["explosion smoke", "explosion", "black smoke rising"], boom=True, post=1.2),
    S("img", "Today, war is still part of daily life in many countries: in Ukraine, in "
      "Sudan, in Gaza, in Yemen, in Myanmar, in eastern Congo... and in many other places "
      "the news rarely talks about.", img="03_soldiers_hill.jpg",
      countries=["Ukraine", "Sudan", "Gaza", "Yemen", "Myanmar", "DR Congo"], boom=True),
    S("img", "Whole cities are reduced to rubble. Schools, hospitals and homes that took "
      "generations to build can disappear in a single night.",
      img="05_ruined_street.jpg"),
    S("clip", "According to the United Nations, more than one hundred and twenty million "
      "people have been forced to flee their homes. That is more than the population of "
      "most countries on Earth.",
      q=["refugees walking", "people walking with luggage", "migrants walking road"],
      big=("120,000,000+", "people forced from their homes"), src="SOURCE: UNHCR"),
    S("img", "And war does not only kill soldiers. Most of its victims are ordinary people "
      "who never chose to fight.", img="04_fallen.jpg", post=1.6),
    S("clip", "Children grow up knowing the sound of sirens better than the sound of a "
      "school bell.", q=["sad child window", "child looking out window", "lonely child"]),
    S("clip", "And war leaves wounds that last long after the guns go quiet: hunger, "
      "trauma, and hatred passed on to the next generation.",
      q=["smoke ruins", "destroyed building", "abandoned ruins"], post=1.8),

    # ------------------------------------------------------------ part three
    card("PART THREE", "Hope", "turn"),
    S("clip", "And yet, history teaches us something else, too. Hope.",
      q=["sunrise over city", "sunrise", "sun rays clouds"], mood="turn", pre=0.8, post=1.4),
    S("clip", "After the Second World War, France and Germany, enemies for centuries, "
      "chose to work together. That choice helped build the peace Europe still lives in today.",
      q=["signing document pen", "pen signing paper", "signing contract"], mood="peace",
      loc="PARIS  —  18 APRIL 1951"),
    S("clip", "In South Africa, Nelson Mandela walked out of prison after twenty-seven years, "
      "and chose reconciliation instead of revenge.",
      q=["hands raised sky", "people walking sunset", "sunrise field silhouette"], mood="peace",
      loc="CAPE TOWN, SOUTH AFRICA  —  11 FEBRUARY 1990"),
    S("clip", "Again and again, ordinary people have shown that the cycle of violence can "
      "be broken.", q=["construction worker bricks", "building construction hands", "rebuilding"],
      mood="peace", post=1.4),

    # ------------------------------------------------------------ part four
    card("PART FOUR", "Building Peace", "peace"),
    S("clip", "So how do we build peace? First, through dialogue. Every war ends at a "
      "negotiating table. The only question is how many lives are lost before we get there.",
      q=["meeting table discussion", "business meeting", "people talking table"],
      mood="peace", tag="1 · Dialogue"),
    S("clip", "Second, through justice: fair laws, honest institutions, and equal rights for "
      "everyone, so that no group feels it has to fight to be heard.",
      q=["justice scale", "courthouse", "law books"], mood="peace", tag="2 · Justice"),
    S("clip", "Third, through education. A child who learns to read, to think, and to "
      "understand others is much harder to turn into a soldier of hate.",
      q=["students classroom", "children school classroom", "kids reading books"],
      mood="peace", tag="3 · Education"),
    S("clip", "Fourth, by fighting poverty. When people have work, food and a future, "
      "they have something worth protecting.",
      q=["farmers working field", "market vendors", "people working together"],
      mood="peace", tag="4 · Fighting Poverty"),
    S("clip", "And fifth, through cooperation between nations: keeping promises, respecting "
      "borders, and solving conflicts together.",
      q=["earth from space", "globe earth", "planet earth"], mood="peace", tag="5 · Cooperation"),
    S("clip", "But peace is not only the work of presidents. It begins with us: in how we "
      "speak to people who are different from us, and how we treat those we disagree with.",
      q=["friends walking together", "group of friends sunset", "people hugging"],
      mood="peace"),
    S("clip", "Peace is not weakness. It takes more courage to forgive than to fight.",
      q=["children playing football street", "kids playing outside", "children running field"],
      mood="peace", post=1.2),
    S("clip", "War destroys in a day what peace builds over a lifetime. So let's choose "
      "peace. Let's make peace.",
      q=["white dove flying", "birds flying sunset", "birds flying sky"],
      mood="peace", post=3.0),

    # ------------------------------------------------------------ ending
    S("title", "", mood="title", pre=0, post=0, img="00_title.jpg", hold=8.0, ending=True),
]


# ---------------------------------------------------------------- helpers
def run(args, desc=""):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        print("CMD:", " ".join(shlex.quote(a) for a in args)[:3000])
        print(p.stderr[-4000:])
        raise RuntimeError(f"ffmpeg failed: {desc}")
    return p


def probe(path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


# ---------------------------------------------------------------- footage
def fetch_footage(work: Path, dry: bool):
    if not dry:
        import stock
        if not (config.PEXELS_API_KEY or "").strip():
            raise SystemExit("PEXELS_API_KEY is missing")
    used = set()
    for i, sc in enumerate(SCENES):
        if sc["kind"] != "clip":
            continue
        dest = work / f"clip_{i:02d}.mp4"
        if dry:
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                 "testsrc2=s=640x360:r=24:d=14", "-c:v", "libx264", "-preset",
                 "ultrafast", str(dest)], "dummy clip")
            sc["clip"], sc["clip_dur"] = str(dest), 14.0
            continue
        chosen, hit = None, None
        for q in sc["q"]:
            for orient, min_side in (("landscape", 1920), ("landscape", 1280), (None, 1280)):
                chosen = stock._search(q, orient, False, used, min_side)
                if chosen:
                    hit = q
                    break
            if chosen:
                break
        if not chosen:
            raise RuntimeError(f"no footage for scene {i}: {sc['q']}")
        _, link, vid, dur = chosen
        used.add(vid)
        stock._download(link, dest)
        sc["clip"], sc["clip_dur"], sc["pexels_id"] = str(dest), float(dur or 10), vid
        print(f"  ✓ scene {i + 1:02d}: pexels#{vid} '{hit}'")


# ---------------------------------------------------------------- voice
async def _tts(text, voice, out):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=RATE, pitch=PITCH).save(str(out))


def narrate(work: Path, dry: bool):
    for i, sc in enumerate(SCENES):
        if sc["kind"] == "card":
            sc["vo"], sc["vo_dur"] = None, 0.0
            sc["dur"] = sc["hold"] + XF
            continue
        if not sc["text"]:
            sc["vo"], sc["vo_dur"] = None, 0.0
            sc["dur"] = sc.get("hold", 6.0) + XF
            continue
        raw = work / f"vo_raw_{i:02d}.mp3"
        if dry:
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                 f"sine=f=180:d={max(2.0, len(sc['text']) / 15):.2f}", str(raw)], "dummy vo")
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
                gTTS(sc["text"], lang="en", tld="co.uk").save(str(raw))
        clean = work / f"vo_{i:02d}.wav"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af",
             "silenceremove=start_periods=1:start_threshold=-50dB,"
             "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse",
             "-ar", "48000", "-ac", "1", str(clean)], "vo trim")
        sc["vo"], sc["vo_dur"] = str(clean), probe(clean)
        sc["dur"] = sc["pre"] + sc["vo_dur"] + sc["post"] + XF
        print(f"  ✓ vo {i + 1:02d}: {sc['vo_dur']:.1f}s")


# ---------------------------------------------------------------- picture
def _finish(mood, bars=True, grain=8):
    f = f"{GRADE[mood]}," if mood in GRADE else ""
    f += f"noise=alls={grain}:allf=t,vignette=PI/4.6,"
    if bars:
        f += (f"drawbox=x=0:y=0:w=iw:h={BAR}:color=black:t=fill,"
              f"drawbox=x=0:y=ih-{BAR}:w=iw:h={BAR}:color=black:t=fill,")
    return f + "format=yuv420p"


def _still_motion(i, d):
    """slow push-in or pull-out on a still (upscaled first so it doesn't judder)."""
    n = int(d * FPS) + 2
    if i % 2:
        z = f"1.10-0.10*on/{n}"
    else:
        z = f"1.0+0.10*on/{n}"
    return (f"scale={W * 2}:{H * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")


def segment(i, sc, work: Path) -> Path:
    out = work / f"seg_{i:02d}.mp4"
    d = sc["dur"]
    enc = ["-t", f"{d:.3f}", "-an", "-r", str(FPS), "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "17", str(out)]
    k = sc["kind"]
    if k == "card":
        vf = ("drawbox=x=0:y=0:w=iw:h=ih:color=0x0b0b0d:t=fill,"
              + _finish("none", bars=True, grain=10))
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             f"color=c=black:s={W}x{H}:r={FPS}:d={d:.3f}", "-vf", vf, *enc], f"card {i}")
    elif k in ("img", "title"):
        src = str(IMG / sc["img"])
        iw, ih = (int(x) for x in subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
             "stream=width,height", "-of", "csv=p=0", src],
            capture_output=True, text=True, check=True).stdout.strip().split(","))
        bg = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"boxblur=40:2,eq=brightness=-0.12:saturation=0.8[bg];")
        if k == "img" and iw / ih < 0.8:
            # tall image: show it big and tilt the camera slowly from top to bottom
            fw = int(W * 0.62) // 2 * 2
            fh = int(ih * fw / iw) // 2 * 2
            span = max(fh - INNER, 0)
            motion = (f"[0:v]scale={fw}:{fh},fps={FPS},"
                      f"crop={fw}:{INNER}:0:'{span}*min(t/{d:.2f},1)'[fg];"
                      f"[bg][fg]overlay=(W-w)/2:{BAR}")
        else:
            fg_h = H if k == "title" else INNER
            motion = (f"[0:v]scale=-2:{fg_h}[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                      f"{_still_motion(i, d)}")
        g = (bg + motion + ","
             + _finish((sc["mood"] if sc["mood"] == "archive" else "img") if k == "img" else "none",
                       bars=(k == "img"),
                       grain=6 if k == "img" else 3) + "[v]")
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", src,
             "-filter_complex", g, "-map", "[v]", *enc], f"image {i}")
    else:
        src_d = sc.get("clip_dur", 10)
        start = min(2.0, (src_d - d) / 3) if src_d > d + 1.5 else 0.0
        slow = ""
        if src_d < d - 0.2:
            slow = f"setpts={min(2.0, (d + 0.3) / max(src_d - start, 1.0)):.3f}*PTS,"
        vf = (f"{slow}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"fps={FPS}," + _finish(sc["mood"]))
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-stream_loop", "-1",
             "-i", sc["clip"], "-vf", vf, *enc], f"clip {i}")
    return out


def picture(work: Path):
    segs = [segment(i, sc, work) for i, sc in enumerate(SCENES)]
    t = 0.0
    for sc in SCENES:
        sc["t0"] = t
        t += sc["dur"] - XF
    total = t + XF
    inputs, chain, last = [], [], "[0:v]"
    for p in segs:
        inputs += ["-i", str(p)]
    for i in range(1, len(segs)):
        prev, cur = SCENES[i - 1], SCENES[i]
        slow = cur["kind"] == "card" or prev["kind"] in ("card", "title") or cur.get("ending")
        tr, dur = ("fadeblack", 1.4) if slow else ("fade", XF)
        off = cur["t0"] - (dur - XF)
        chain.append(f"{last}[{i}:v]xfade=transition={tr}:duration={dur}:offset={off:.3f}[x{i}]")
        last = f"[x{i}]"
    chain.append(f"{last}fade=t=in:st=0:d=2,fade=t=out:st={total - 3:.3f}:d=3[v]")
    out = work / "picture.mp4"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(chain),
         "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
         "-pix_fmt", "yuv420p", str(out)], "xfade chain")
    return out, total


# ---------------------------------------------------------------- sound
def score(work: Path, total: float) -> Path:
    T = f"{total:.3f}"
    a = SCENES[1]["t0"]                                           # end of opening
    b = next(sc["t0"] for sc in SCENES if sc["mood"] == "turn")  # hope begins
    war_gain = f"clip((t-{a:.2f})/4,0,1)*clip(({b + 1:.2f}-t)/4,0,1)"
    pad_gain = f"clip(({a + 1:.2f}-t)/4,0,1)+clip((t-{b:.2f})/7,0,1)*clip(({T}-t)/6,0,1)"
    rumble = (f"anoisesrc=c=brown:a=0.5:d={T}:r=48000,lowpass=f=110,lowpass=f=110,"
              f"volume=0.55,tremolo=f=0.13:d=0.6,volume='{war_gain}':eval=frame")
    drone = (f"sine=f=55:d={T}:r=48000[a0];sine=f=65.41:d={T}:r=48000[a1];"
             f"sine=f=82.41:d={T}:r=48000[a2];sine=f=98:d={T}:r=48000[a3];"
             f"[a0][a1][a2][a3]amix=inputs=4,volume=0.55,tremolo=f=0.2:d=0.3,"
             f"volume='{war_gain}':eval=frame")
    notes = [110, 110.6, 164.81, 220, 220.9, 277.18, 329.63, 440]
    pad_in = ";".join(f"sine=f={f}:d={T}:r=48000[p{k}]" for k, f in enumerate(notes))
    pad = (f"{pad_in};{''.join(f'[p{k}]' for k in range(len(notes)))}"
           f"amix=inputs={len(notes)},volume=0.95,lowpass=f=1000,tremolo=f=0.25:d=0.25,"
           f"aecho=0.8:0.7:120|260:0.3|0.2,volume='{pad_gain}':eval=frame")
    booms, k = [], 0
    for sc in SCENES:
        if sc["mood"] != "war" or sc["kind"] == "card" or not (sc.get("boom") or sc.get("big")
                                                               or sc["kind"] == "img"):
            continue
        k += 1
        at = sc["t0"] + 0.3
        booms.append(f"anoisesrc=c=brown:a=1:d=3.5:r=48000,lowpass=f={85 + 9 * (k % 4)},"
                     f"afade=t=in:d=0.03,afade=t=out:st=0.05:d=3.4,"
                     f"volume={1.5 if sc.get('boom') else 0.8},adelay={int(at * 1000)}:all=1,"
                     f"apad=whole_dur={T}[b{k}]")
    labels = "".join(f"[b{j}]" for j in range(1, k + 1))
    g = (f"{rumble}[r];{drone}[dm];{pad}[pd];" + "".join(x + ";" for x in booms) +
         f"[r][dm][pd]{labels}amix=inputs={3 + k}:normalize=0,"
         f"atrim=0:{T},volume=0.33,alimiter=limit=0.7[m]")
    out = work / "score.wav"
    run(["ffmpeg", "-y", "-v", "error", "-filter_complex", g, "-map", "[m]",
         "-ac", "2", "-ar", "48000", str(out)], "score")
    return out


def voice_track(work: Path, total: float) -> Path:
    inputs, parts, n = [], [], 0
    for sc in SCENES:
        if not sc["vo"]:
            continue
        inputs += ["-i", sc["vo"]]
        parts.append(f"[{n}:a]adelay={int((sc['t0'] + sc['pre']) * 1000)}:all=1,"
                     f"apad=whole_dur={total:.3f}[v{n}]")
        n += 1
    g = (";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(n)) +
         f"amix=inputs={n}:normalize=0,atrim=0:{total:.3f},"
         "highpass=f=75,lowpass=f=11500,"
         "equalizer=f=180:t=q:w=1:g=2.5,equalizer=f=3200:t=q:w=1.2:g=-1.5,"
         "acompressor=threshold=-20dB:ratio=3:attack=8:release=180,"
         "aecho=0.85:0.9:28|47:0.10|0.06[vo]")
    out = work / "voice.wav"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", g,
         "-map", "[vo]", "-ac", "2", "-ar", "48000", str(out)], "voice track")
    return out


# ---------------------------------------------------------------- text
def tc(t):
    t = max(0.0, t)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def captions(work: Path, total: float) -> Path:
    sc_ = H / 1080
    ev = []

    def add(layer, a, b, style, text, fx="{\\fad(250,250)}"):
        ev.append(f"Dialogue: {layer},{tc(a)},{tc(b)},{style},,0,0,0,,{fx}{text}")

    def f(v):
        return max(1, round(v * sc_))

    def typewriter(a, b, text, cps=22):
        """documentary location line, typed out letter by letter."""
        for n in range(1, len(text) + 1):
            s0 = a + (n - 1) / cps
            s1 = a + n / cps if n < len(text) else b
            add(1, s0, s1, "Loc", text[:n] + ("_" if n < len(text) else ""), "")

    for sc in SCENES:
        t0, end = sc["t0"], sc["t0"] + sc["dur"] - XF
        if sc["kind"] == "card":
            add(2, t0 + 0.6, end - 0.2, "CardNum", sc["num"], "{\\fad(600,500)}")
            add(2, t0 + 0.9, end - 0.2, "Card", sc["title"], "{\\fad(700,500)}")
            continue
        if sc["vo"] and os.environ.get("MP_SUBS") == "1":   # subtitles off by default
            start = t0 + sc["pre"]
            chunks = [c.strip() for c in re.split(r"(?<=[.?!:])\s+", sc["text"]) if c.strip()]
            n = sum(len(c) for c in chunks)
            t = start
            for c in chunks:
                d = sc["vo_dur"] * len(c) / n
                add(0, t, t + d + 0.25, "Sub", c, "{\\fad(150,150)}")
                t += d
        if sc.get("loc"):
            typewriter(t0 + 0.9, end - 0.4, sc["loc"])
        if sc.get("src"):
            add(1, t0 + 1.4, end - 0.4, "Src", sc["src"], "{\\fad(500,400)}")
        if sc.get("tag"):
            bar_y = H - BAR - f(118)
            add(1, t0 + 0.8, end - 0.3, "Line",
                f"{{\\pos({f(90)},{bar_y})\\fad(500,400)\\p1}}m 0 0 l {f(5)} 0 {f(5)} {f(64)} 0 {f(64)}{{\\p0}}", "")
            add(1, t0 + 0.8, end - 0.3, "Tag", sc["tag"].upper(), "{\\fad(500,400)}")
        if sc.get("big"):
            num, cap = sc["big"]
            add(1, t0 + 0.7, end - 0.4, "Big", num, "{\\fad(700,500)}")
            add(1, t0 + 1.2, end - 0.4, "BigCap", cap, "{\\fad(700,500)}")
        if sc.get("countries"):
            step = max(0.55, (sc["vo_dur"] * 0.8) / len(sc["countries"]))
            for j, c in enumerate(sc["countries"]):
                y = BAR + int((70 + j * 62) * sc_)
                add(1, t0 + sc["pre"] + 0.6 + j * step, end - 0.3, "Country",
                    f"{{\\pos({int(80 * sc_)},{y})\\fad(400,400)}}— {c}", "")
        if sc.get("ending"):
            pass
    # names credit over the very last seconds of the closing title card
    ass = work / "film.ass"
    ass.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{SERIF},{f(42)},&H00EAEAEA,&H00EAEAEA,&H00000000,&H00000000,0,0,0,0,100,100,0.5,0,1,1.2,0,2,{f(160)},{f(160)},{f(40)},1
Style: Card,{SERIF},{f(96)},&H00F0F0F0,&H00F0F0F0,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,0,0,5,0,0,0,1
Style: CardNum,{SERIF},{f(34)},&H0088C8E8,&H0088C8E8,&H00000000,&H00000000,0,0,0,0,100,100,{f(12)},0,1,0,0,8,0,0,{f(400)},1
Style: Tag,{SERIF},{f(46)},&H00F2F2F2,&H00F2F2F2,&H00000000,&H96000000,0,0,0,0,100,100,{f(4)},0,1,0,{f(2)},1,{f(115)},0,{BAR + f(60)},1
Style: Loc,DejaVu Sans Mono,{f(30)},&H00E8E8E8,&H00E8E8E8,&H00000000,&H96000000,0,0,0,0,100,100,{f(3)},0,1,0,{f(2)},1,{f(90)},0,{BAR + f(40)},1
Style: Src,DejaVu Sans,{f(24)},&H00B0B0B0,&H00B0B0B0,&H00000000,&H96000000,0,0,0,0,100,100,{f(3)},0,1,0,{f(2)},3,0,{f(90)},{BAR + f(30)},1
Style: Line,DejaVu Sans,{f(20)},&H0088C8E8,&H0088C8E8,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Big,{SERIF},{f(150)},&H00F5F5F5,&H00F5F5F5,&H00000000,&H96000000,1,0,0,0,100,100,2,0,1,0,{f(4)},5,0,0,0,1
Style: BigCap,{SERIF},{f(44)},&H0088C8E8,&H0088C8E8,&H00000000,&H96000000,0,1,0,0,100,100,2,0,1,0,{f(3)},2,0,0,{BAR + f(150)},1
Style: Country,{SERIF},{f(50)},&H00F2F2F2,&H00F2F2F2,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,0,{f(3)},7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n", encoding="utf-8")
    return ass


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    out_dir = config.OUT
    work = out_dir / "make_peace_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    print("• footage"); fetch_footage(work, a.dry_run)
    print("• voice-over"); narrate(work, a.dry_run)
    print("• picture"); pic, total = picture(work)
    print(f"  timeline {total:.1f}s ({total / 60:.1f} min)")
    print("• sound"); mus = score(work, total); vo = voice_track(work, total)
    ass = captions(work, total)

    final = out_dir / "make_peace.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(pic), "-i", str(vo), "-i", str(mus),
         "-filter_complex",
         "[1:a]asplit=2[v][sc];[2:a][sc]sidechaincompress=threshold=0.04:ratio=4:"
         "attack=30:release=500[md];"
         "[v][md]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]",
         "-map", "0:v", "-map", "[a]", "-vf", f"subtitles={shlex.quote(str(ass))}",
         "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-maxrate", "4500k",
         "-bufsize", "9000k", "-tune", "grain", "-profile:v", "high",
         "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", str(final)], "final")

    meta = {
        "title": "Make Peace — Why Wars Begin and How Peace Is Built",
        "duration": round(total, 1),
        "script": [sc["text"] for sc in SCENES if sc["text"]],
        "clips": [{"scene": i + 1, "pexels_id": sc.get("pexels_id")}
                  for i, sc in enumerate(SCENES) if sc["kind"] == "clip"],
    }
    (out_dir / "make_peace.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"✓ done: {final} ({final.stat().st_size // 1024 // 1024}MB, {total:.1f}s)")


if __name__ == "__main__":
    main()
