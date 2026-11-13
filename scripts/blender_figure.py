"""مجسّم عضلي ثلاثي الأبعاد حقيقي (Blender / bpy) بأسلوب فيديوهات التمارين التشريحية.

الجسم مبني من Metaballs (تندمج بنعومة فتعطي شكل عضلات حقيقياً: صدر، بطن سداسي،
أكتاف، بايسبس…)، والعضلة المستهدفة كائن منفصل بمادة متوهجة.

    python scripts/blender_figure.py --style clay --out out/style_clay.png
    python scripts/blender_figure.py --style anatomy --wrist 30 --out a.png
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import bpy
from mathutils import Euler, Quaternion, Vector

STYLES = ("clay", "anatomy", "chrome")


# ------------------------------------------------------------------ أدوات
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def quat(rx=0, ry=0, rz=0) -> Quaternion:
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz))).to_quaternion()


def look_quat(a, b) -> Quaternion:
    """دوران يجعل محور X للعنصر يتجه من a إلى b (للكبسولات)."""
    d = (Vector(b) - Vector(a)).normalized()
    return Vector((1, 0, 0)).rotation_difference(d)


class Meta:
    """أجزاء شبكية (إهليلجات/كبسولات) تُدمج في جسم واحد عبر Voxel Remesh ثم تُنعَّم."""

    def __init__(self, name, mat, voxel=0.005, smooth=0.7, repeat=12):
        self.name, self.mat = name, mat
        self.voxel, self.smooth, self.repeat = voxel, smooth, repeat
        self.parts = []

    def _sphere(self, co, size, rot: Quaternion):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1.0, location=co)
        o = bpy.context.object
        o.scale = size
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = rot
        self.parts.append(o)
        return o

    def ell(self, co, size, rot=(0, 0, 0), stiff=2.0, neg=False):
        if neg:
            return None
        q = quat(*rot) if isinstance(rot, tuple) else rot
        return self._sphere(co, size, q)

    def cap(self, a, b, r, stiff=2.0, neg=False):
        if neg:
            return None
        a, b = Vector(a), Vector(b)
        n = max(2, int((b - a).length / (r * 0.5)) + 1)
        for i in range(n):
            self._sphere(a + (b - a) * (i / (n - 1)), (r, r, r), Quaternion())

    def muscle(self, a, b, thick, width=None, stiff=2.0, roll=0.0):
        a, b = Vector(a), Vector(b)
        q = look_quat(a, b)
        if roll:
            q = q @ quat(roll, 0, 0)
        return self._sphere((a + b) / 2, ((b - a).length / 2, width or thick, thick), q)

    def finalize(self):
        bpy.ops.object.select_all(action="DESELECT")
        for o in self.parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active = self.parts[0]
        bpy.ops.object.join()
        o = bpy.context.object
        o.name = self.name
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        rm = o.modifiers.new("remesh", "REMESH")
        rm.mode = "VOXEL"
        rm.voxel_size = self.voxel
        sm = o.modifiers.new("smooth", "SMOOTH")
        sm.factor = self.smooth
        sm.iterations = self.repeat
        o.data.materials.append(self.mat)
        bpy.ops.object.shade_smooth()
        self.obj = o
        return o


# ------------------------------------------------------------------ المواد
def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def mat_principled(name, color, rough=0.45, metal=0.0, sss=0.0, coat=0.0):
    m, nt, out = node_mat(name)
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if sss:
        p.inputs["Subsurface Weight"].default_value = sss
        p.inputs["Subsurface Radius"].default_value = (0.08, 0.06, 0.05)
        p.inputs["Subsurface Scale"].default_value = 0.05
    if coat:
        p.inputs["Coat Weight"].default_value = coat
    nt.links.new(p.outputs[0], out.inputs[0])
    return m


def mat_fibers(name, base, glow, strength, fiber_scale=55.0, rough=0.4, emit_base=False):
    """مادة عضلة بألياف (Wave texture) مع توهج."""
    m, nt, out = node_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0, 0.25)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = fiber_scale
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (*[c * 0.55 for c in glow], 1)
    ramp.color_ramp.elements[1].color = (*glow, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs[0], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*base, 1)
    p.inputs["Roughness"].default_value = rough
    nt.links.new(ramp.outputs[0], p.inputs["Base Color"])
    nt.links.new(ramp.outputs[0], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = strength
    nt.links.new(p.outputs[0], out.inputs[0])
    return m


def style_materials(style):
    if style == "clay":
        body = mat_principled("Body", (0.62, 0.62, 0.65), rough=0.5, sss=0.15)
        target = mat_fibers("Target", (1, 0.3, 0.05), (1.0, 0.26, 0.02), 3.0)
    elif style == "anatomy":
        body = mat_fibers("Body", (0.45, 0.07, 0.06), (0.42, 0.06, 0.05), 0.0, fiber_scale=70, rough=0.35)
        target = mat_fibers("Target", (1, 0.5, 0.1), (1.0, 0.55, 0.08), 5.0)
    else:  # chrome
        body = mat_principled("Body", (0.32, 0.34, 0.38), rough=0.22, metal=0.85, coat=0.4)
        target = mat_fibers("Target", (1, 0.4, 0.1), (1.0, 0.38, 0.05), 5.0)
    return body, target


# ------------------------------------------------------------------ الجسم
def build_body(body_mat, target_mat, wrist_deg=10.0):
    B = Meta("Body", body_mat)
    T = Meta("Target", target_mat)       # اسم مختلف → لا يندمج مع الجسم (حد واضح عند المرفق)

    # الحوض والجذع (ميلان بسيط للأمام)
    B.ell((0, 0.02, 0.10), (0.17, 0.12, 0.11))
    B.ell((0, -0.01, 0.30), (0.135, 0.095, 0.15))                     # البطن
    B.ell((0, 0.01, 0.53), (0.185, 0.115, 0.16), rot=(-8, 0, 0))     # القفص
    for sx in (-1, 1):
        B.ell((sx * 0.083, -0.085, 0.585), (0.092, 0.048, 0.066), rot=(-10, 0, sx * 10), stiff=3)  # الصدر
        B.ell((sx * 0.15, 0.03, 0.47), (0.06, 0.07, 0.15), rot=(0, sx * -12, 0))               # الظهر العريض
        B.ell((sx * 0.13, -0.06, 0.33), (0.035, 0.05, 0.12), rot=(0, sx * 8, 0), stiff=2.5)     # المائلة
        # البطن السداسي
        for z in (0.22, 0.31, 0.40):
            B.ell((sx * 0.042, -0.094, z), (0.038, 0.016, 0.036), stiff=4)
    # أخاديد البطن
    B.cap((0, -0.115, 0.17), (0, -0.115, 0.46), 0.012, stiff=3, neg=True)
    for z in (0.265, 0.355):
        B.cap((-0.07, -0.112, z), (0.07, -0.112, z), 0.009, stiff=3, neg=True)
    B.ell((0, 0.04, 0.655), (0.13, 0.055, 0.04), rot=(-15, 0, 0))      # الترابيس
    B.cap((0, 0.0, 0.64), (0, -0.07, 0.75), 0.06)                       # الرقبة
    B.ell((0, -0.125, 0.83), (0.08, 0.098, 0.11), rot=(-50, 0, 0))      # الرأس (منحنٍ للأسفل)

    # الذراعان
    for sx in (-1, 1):
        sh = Vector((sx * 0.2, 0.0, 0.625))
        el = Vector((sx * 0.235, -0.13, 0.355))
        wr = Vector((sx * 0.165, -0.47, 0.375))
        B.ell(sh + Vector((sx * 0.01, -0.005, -0.01)), (0.064, 0.07, 0.072), rot=(0, sx * 20, 0))  # الكتف
        B.cap(sh, el, 0.04)
        B.muscle(sh + Vector((0, -0.035, -0.03)), el + Vector((0, -0.02, 0.04)), 0.04, stiff=3)  # بايسبس
        B.muscle(sh + Vector((sx * 0.01, 0.04, -0.05)), el + Vector((0, 0.03, 0.03)), 0.042, stiff=3)  # ترايسبس
        # الساعد (العضلة المستهدفة)
        T.cap(el, wr, 0.036)
        T.muscle(el + (wr - el) * 0.05, el + (wr - el) * 0.6 + Vector((0, 0, 0.012)), 0.05, 0.058, stiff=3)
        # اليد (الكف للأعلى) + الرسغ يدور حول محور X
        d = (wr - el).normalized()
        ang = math.radians(wrist_deg)
        hd = Vector((d.x, d.y * math.cos(ang), math.sin(ang) * abs(d.y) + d.z)).normalized()
        up = Vector((0, 0, 1))
        B.cap(wr - d * 0.01, wr + hd * 0.02, 0.03)                       # الرسغ
        palm = wr + hd * 0.055
        B.ell(palm, (0.055, 0.043, 0.022), rot=look_quat(wr, wr + hd))   # الكف
        B.cap(palm + hd * 0.035, palm + hd * 0.06 + up * 0.035, 0.019)   # الأصابع ملتفة
        B.cap(palm + Vector((-sx * 0.04, 0, 0)), palm + Vector((-sx * 0.045, 0, 0.04)) + hd * 0.03, 0.016)  # الإبهام
        add_dumbbell(sx, palm + hd * 0.045 + up * 0.026)

    for M in (B, T):
        M.finalize().rotation_euler = (math.radians(-6), 0, 0)
    return B, T


def add_dumbbell(sx, c):
    iron = bpy.data.materials.get("Iron") or mat_principled("Iron", (0.06, 0.06, 0.065), rough=0.35, metal=0.6)
    steel = bpy.data.materials.get("Steel") or mat_principled("Steel", (0.7, 0.7, 0.72), rough=0.2, metal=1.0)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.014, depth=0.16, location=c, rotation=(0, math.radians(90), 0))
    h = bpy.context.object
    h.data.materials.append(steel)
    for off in (-0.075, 0.075):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.026, vertices=48,
                                            location=c + Vector((off, 0, 0)), rotation=(0, math.radians(90), 0))
        p = bpy.context.object
        p.data.materials.append(iron)
        bev = p.modifiers.new("b", "BEVEL")
        bev.width = 0.006
        bev.segments = 3
        bpy.ops.object.shade_smooth()


def box(loc, size, mat, rot=(0, 0, 0), bevel=0.02):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=[math.radians(r) for r in rot])
    o = bpy.context.object
    o.scale = [s / 2 for s in size]
    bpy.ops.object.transform_apply(scale=True)
    m = o.modifiers.new("b", "BEVEL")
    m.width = bevel
    m.segments = 4
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o


def build_bench():
    pad = mat_principled("Pad", (0.035, 0.035, 0.038), rough=0.55)
    frame = mat_principled("Frame", (0.18, 0.18, 0.19), rough=0.3, metal=0.9)
    box((0, -0.36, 0.28), (0.7, 0.5, 0.09), pad, bevel=0.035)              # وسادة البنش
    box((0, 0.1, -0.02), (0.55, 0.45, 0.09), pad, bevel=0.035)             # المقعد
    box((0, -0.36, 0.0), (0.08, 0.08, 0.6), frame, rot=(30, 0, 0))
    box((0, -0.15, -0.25), (0.08, 0.08, 0.6), frame, rot=(-40, 0, 0))
    box((0, -0.3, -0.53), (0.6, 0.09, 0.06), frame)


# ------------------------------------------------------------------ المشهد
def setup_scene(style, w, h, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "Medium High Contrast"
    sc.view_settings.exposure = -1.7

    world = bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.004, 0.0045, 0.006, 1)

    # أرضية/خلفية منحنية داكنة
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, -0.56))
    bpy.context.object.data.materials.append(mat_principled("Floor", (0.012, 0.012, 0.014), rough=0.6))
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 2.2, 2), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(mat_principled("Wall", (0.01, 0.011, 0.014), rough=0.9))

    def area(name, loc, target, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        ld.color = color
        o = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    area("Key", (-1.4, -1.6, 2.2), (0, -0.2, 0.5), 150, 1.6)
    area("Fill", (1.8, -1.2, 0.8), (0, -0.2, 0.5), 50, 2.0, (0.85, 0.9, 1.0))
    area("Rim", (1.0, 1.3, 1.8), (0, 0, 0.6), 200, 0.8, (0.7, 0.82, 1.0))
    area("Top", (0, 0, 2.6), (0, -0.1, 0.5), 70, 1.0)

    cam_d = bpy.data.cameras.new("Cam")
    cam_d.lens = 40
    cam = bpy.data.objects.new("Cam", cam_d)
    sc.collection.objects.link(cam)
    cam.location = (0.62, -1.3, 1.22)
    cam.rotation_euler = (Vector((0.0, -0.2, 0.48)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam


def render(style, out, w=720, h=1280, samples=48, wrist=10.0):
    reset()
    body, target = style_materials(style)
    setup_scene(style, w, h, samples)
    build_body(body, target, wrist)
    build_bench()
    sc = bpy.context.scene
    sc.render.filepath = str(Path(out).resolve())
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="clay", choices=STYLES)
    ap.add_argument("--out", default="out/style.png")
    ap.add_argument("--w", type=int, default=720)
    ap.add_argument("--h", type=int, default=1280)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--wrist", type=float, default=10.0)
    a = ap.parse_args()
    render(a.style, a.out, a.w, a.h, a.samples, a.wrist)
