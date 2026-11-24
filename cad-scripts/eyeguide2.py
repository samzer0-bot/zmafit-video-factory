# Eye-drop guide v2: + drop-count dial ring with clicks, pointer, dust cap, two size spacers, right/left ID clips.
import math, numpy as np, trimesh
from manifold3d import Manifold as M, CrossSection as CS, FillRule
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
exec(open('eyeguide.py').read().split("def tm(m)")[0].replace('OUT="/home/user/zmafit-video-factory/eye-drop-guide-stl/"','OUT="/home/user/zmafit-video-factory/eye-drop-guide-stl/v2/"'))
OUT="/home/user/zmafit-video-factory/eye-drop-guide-stl/v2/"
fp=FontProperties(family="DejaVu Sans",weight="bold")
def label(txt,size,cx,cy,rot,z,h=0.6):
    tp=TextPath((0,0),txt,size=size,prop=fp); polys=[p for p in tp.to_polygons() if len(p)>2]
    allp=np.vstack(polys); c=(allp.min(0)+allp.max(0))/2
    cs=CS([[(float(x-c[0]),float(y-c[1])) for x,y in p] for p in polys],FillRule.EvenOdd).rotate(rot).translate([cx,cy])
    return M.extrude(cs,h).translate([0,0,z])
# --- guide additions: click ribs, retaining bump, pointer ---
for k in range(6):
    a=k*60
    guide+=box(20.8,-0.8,2.4,0.9,1.6,4.6).rotate([0,0,a])
guide+=zcyl(1.4,0.6,21.0,21.8)                                   # bottom retaining bump (chamfered)
guide+=M.batch_hull([box(-1.6,-20.6,8,3.2,0.5,1.6),box(-0.4,-25.4,8,0.8,0.5,1.0)])   # pointer over the dial
# --- drop-count dial ring (0..5), snaps over the rim from the face side ---
ring=zcyl(2.2,5,27,27)-zcyl(2.1,5.2,21.5)
for k in range(6):
    a=-90+k*60
    ring+=label(str(k),3.6,24.3*math.cos(math.radians(a)),24.3*math.sin(math.radians(a)),a+90,7.2,0.6)
for k in range(24): ring-=box(26.6,-0.5,2.1,0.8,1.0,5.2).rotate([0,0,k*15])   # grip knurl
ring=ring.translate([0,0,-2.2])
# --- dust cap for the eye rim ---
cap=zcyl(0,1.6,23.5)+(zcyl(1.6,2.2,23.5)-zcyl(1.5,2.4,22.0))+(zcyl(3.4,0.4,22.0)-zcyl(3.3,0.6,21.35))
# --- spacers ---
slim=zcyl(0,8,13.4)-zcyl(-0.1,8.2,9.6); slim-=box(-1,-14,-0.1,2,6,8.3)
xslim=zcyl(0,8,13.4)-zcyl(-0.1,8.2,7.7); xslim-=box(-1,-14,-0.1,2,7,8.3)
# --- right / left ID clips (slide onto a wing from the bottle side) ---
def idclip(ch):
    c=box(0,-8.6,0,3.6,17.2,8)-box(-0.1,-7.2,-0.1,2.5,14.4,8.2)
    c+=box(-0.9,-8.6,0,1.0,1.4,8)+box(-0.9,7.2,0,1.0,1.4,8)       # small hooks
    c+=label(ch,6.5,3.6,0,-90,4,0.8).rotate([0,90,0]).translate([0,0,0]) if False else box(0,0,0,0,0,0)
    return c
def idclip2(ch):
    base=box(0,0,0,17.2,8,3.6)-box(1.4,-0.1,1.1,14.4,8.2,2.6)      # printed flat: U open upward
    base+=box(0,0,3.6,1.4,8,0.9)+box(15.8,0,3.6,1.4,8,0.9)
    base-=label(ch,6.0,0,4,0,-0.1,0.7).scale([-1,1,1]).translate([8.6,0,0])   # engraved (mirrored) on the outer face
    return base
clips={"id_clip_right_ي":idclip2("ي"),"id_clip_left_س":idclip2("س")}
import os; os.makedirs(OUT,exist_ok=True)
def tm(m): me=m.to_mesh(); return trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts)
allp={"eye_drop_guide_v2":guide,"drop_count_ring":ring,"dust_cap":cap,"spacer_22mm_bottles":slim,"spacer_17mm_bottles":xslim}
allp.update(clips)
for n,m in allp.items():
    t=tm(m); t.apply_translation(-t.bounds[0]); t.export(OUT+n+".stl"); print(n,[round(float(v),1) for v in t.extents],"genus",m.genus())
print("ring∩guide %.2f"%(ring.translate([0,0,2.2])^guide).volume(), "cap∩guide %.2f"%(cap.translate([0,0,-1.6])^guide).volume())
