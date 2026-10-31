"""Cut the single voiceover take into one clip per scene -> public/vo/<lang>/<key>.mp3

Segment boundaries come from `ffmpeg -af silencedetect` on the raw take.
Each clip is sped up slightly (pitch preserved) so it fits its scene slot in timeline.json.
Usage: python3 vo-src/split_vo.py
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / 'src/timeline.json').read_text())
FPS = TL['fps']

SEGMENTS = {
    'en': {
        'raw': 'en-raw.mp3',
        'tempo': 1.12,
        'clips': {
            'hook0': (0.00, 2.36),
            'hook1': (2.64, 6.24, 1.15),
            'hook2': (7.03, 9.56),
            'hook3': (10.03, 13.90, 1.22),
            'questions': (14.58, 16.91),
            'twoPlans': (17.52, 20.87),
            'plan': (22.21, 28.02),
            'pdf': (28.69, 31.36, 1.15),
            'price': (31.89, 35.78, 1.18),
            'cta': (36.60, 40.28, 1.2),
        },
    },
}
extra = ROOT / 'vo-src/segments_ar.json'
if extra.exists():
    SEGMENTS['ar'] = json.loads(extra.read_text())


def scene_end_sec(key):
    scene = 'hook' if key.startswith('hook') else key
    s = TL['scenes'][scene]
    return (s['from'] + s['duration']) / FPS, (s['from'] + TL['vo'][scene]) / FPS


for lang, cfg in SEGMENTS.items():
    out = ROOT / 'public/vo' / lang
    out.mkdir(parents=True, exist_ok=True)
    for key, seg in cfg['clips'].items():
        a, b = seg[0], seg[1]
        tempo = seg[2] if len(seg) > 2 and seg[2] else cfg['tempo']
        if len(seg) > 3:  # clip taken from another take
            raw = ROOT / 'vo-src' / seg[3]
        else:
            raw = ROOT / 'vo-src' / cfg['raw']
        dst = out / f'{key}.mp3'
        subprocess.run(
            ['ffmpeg', '-loglevel', 'error', '-y', '-ss', str(a), '-to', str(b), '-i', str(raw),
             '-af', f'atempo={tempo},afade=t=in:d=0.02,areverse,afade=t=in:d=0.06,areverse,loudnorm=I=-15:TP=-1.5,aresample=44100',
             '-ac', '2', '-b:a', '192k', str(dst)],
            check=True,
        )
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(dst)], capture_output=True, text=True).stdout)
        end, start = scene_end_sec(key)
        if key.startswith('hook'):  # hook may overflow until the questions voice line starts
            q = TL['scenes']['questions']
            end = (q['from'] + TL['vo']['questions']) / FPS - 0.05
        limit = end - start
        flag = 'OK ' if dur <= limit else 'TOO LONG'
        print(f'{flag} {lang}/{key}: {dur:.2f}s (slot {limit:.2f}s)')
