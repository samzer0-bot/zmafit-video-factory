"""توليد رسومات التمارين بنفس أسلوب رسومات القناة (مجاني): Gemini image ثم Pollinations احتياطاً."""
import base64, json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

KEY = os.environ.get("GEMINI_API_KEY", "")
BASE = "https://generativelanguage.googleapis.com/v1beta"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "gen"); OUT.mkdir(exist_ok=True)
REF = Path("assets/anatomy/front.jpg")

STYLE = ("Detailed anatomical pencil illustration in the exact style of the reference image: the whole man is drawn in fine "
         "graphite cross-hatching, grayscale, showing every muscle fiber like a medical anatomy atlas. Same man as the reference: "
         "athletic, short buzz cut, short beard, black athletic shorts, black running sneakers with white soles. "
         "ONLY the working muscles listed are colored in vivid flat red-orange (same red-orange as the reference) with the fiber "
         "texture visible through the color; every other muscle stays grayscale. Pure plain white background, full body visible, "
         "centered, generous even margins. No text, no labels, no arrows, no watermark, no logo.")

EX = {
 "pullup":   ("portrait", "Pose: hanging from a horizontal pull-up bar mid pull-up, chin near the bar, seen from behind. Red muscles: latissimus dorsi (lats), biceps, rear shoulders."),
 "plank":    ("landscape", "Pose: forearm plank on the floor, body in a straight line, seen from the side. Red muscles: rectus abdominis (abs), obliques, front shoulders."),
 "lunge":    ("portrait", "Pose: forward lunge, front knee bent 90 degrees, back knee near the floor, seen from the side at a three-quarter angle. Red muscles: quadriceps, glutes, hamstrings."),
 "bridge":   ("landscape", "Pose: glute bridge lying on the back on the floor, feet flat, hips raised high, seen from the side. Red muscles: glutes, hamstrings, lower back."),
 "dips":     ("portrait", "Pose: bench dips with hands on a low bench behind him, elbows bent, legs extended forward, seen from the side. Red muscles: triceps, front shoulders, lower chest."),
 "pike":     ("landscape", "Pose: pike push-up, hips high in an inverted V, head lowered toward the floor between the hands, seen from the side. Red muscles: shoulders (deltoids), triceps, upper chest."),
 "calfraise":("portrait", "Pose: standing calf raise on the tips of the toes on the edge of a step, seen from behind. Red muscles: calves (gastrocnemius and soleus) only."),
 "legraise": ("landscape", "Pose: lying leg raise on the floor, legs straight and lifted to 90 degrees, hands by the sides, seen from the side. Red muscles: lower abs, hip flexors, obliques."),
 "superman": ("landscape", "Pose: superman exercise lying face down, arms and legs lifted off the floor, seen from the side. Red muscles: lower back (erector spinae), glutes, hamstrings, rear shoulders."),
 "climber":  ("landscape", "Pose: mountain climber in a high plank, one knee driven toward the chest, seen from the side. Red muscles: abs, hip flexors, front shoulders, quadriceps."),
}


def post(url, body, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def gemini_models():
    if not KEY: return []
    try:
        with urllib.request.urlopen(f"{BASE}/models?key={KEY}&pageSize=200", timeout=60) as r:
            ms = json.loads(r.read()).get("models", [])
        names = [m["name"].split("/")[-1] for m in ms if "image" in m["name"] and "generateContent" in m.get("supportedGenerationMethods", [])]
        print("Gemini image models:", names)
        return sorted(names, key=lambda n: ("preview" in n, n))
    except Exception as e:
        print("models list failed:", e); return []


def gen_gemini(models, prompt, aspect, dest):
    ref = base64.b64encode(REF.read_bytes()).decode()
    for m in models:
        try:
            body = {"contents": [{"parts": [
                {"text": "Reference image for the drawing style and the man's appearance:"},
                {"inline_data": {"mime_type": "image/jpeg", "data": ref}},
                {"text": STYLE + " " + prompt}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"],
                                     "imageConfig": {"aspectRatio": "9:16" if aspect == "portrait" else "16:9"}}}
            d = post(f"{BASE}/models/{m}:generateContent?key={KEY}", body)
            for p in d["candidates"][0]["content"]["parts"]:
                blob = p.get("inline_data") or p.get("inlineData")
                if blob:
                    dest.write_bytes(base64.b64decode(blob["data"])); print("  OK gemini", m); return True
            print("  no image from", m)
        except Exception as e:
            msg = getattr(e, "read", lambda: b"")()[:300]
            print("  gemini", m, "failed:", e, msg)
    return False


def gen_pollinations(prompt, aspect, dest, seed):
    w, h = (1152, 2048) if aspect == "portrait" else (2048, 1152)
    q = urllib.parse.quote(STYLE.replace("in the exact style of the reference image", "") + " " + prompt)
    url = f"https://image.pollinations.ai/prompt/{q}?width={w}&height={h}&model=flux&nologo=true&seed={seed}"
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=240) as r:
                data = r.read()
            if len(data) > 30000:
                dest.write_bytes(data); print("  OK pollinations"); return True
        except Exception as e:
            print("  pollinations failed:", e); time.sleep(10)
    return False


if __name__ == "__main__":
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else list(EX)
    models = gemini_models()
    for i, name in enumerate(only):
        aspect, p = EX[name]
        print("•", name)
        ok = gen_gemini(models, p, aspect, OUT / f"g_{name}.png") if models else False
        ok2 = gen_pollinations(p, aspect, OUT / f"p_{name}.jpg", 1000 + i)
        print("  result:", ok, ok2)
