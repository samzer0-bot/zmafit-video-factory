# Eye-drop guide: rests on the eye socket, centres an inverted bottle, two flexible wings squeeze it.
import math, numpy as np, trimesh
from manifold3d import Manifold as M
OUT="/home/user/zmafit-video-factory/eye-drop-guide-stl/"
def zcyl(z,h,r1,r2=None,seg=96): return M.cylinder(h,r1,r1 if r2 is None else r2,seg).translate([0,0,z])
def box(x,y,z,dx,dy,dz): return M.cube([dx,dy,dz]).translate([x,y,z])
# eye cup (face side on the bed, z=0) : soft rounded rim
cup=zcyl(0,1.2,19.6,21)+zcyl(1.2,6.8,21)-zcyl(-0.1,8.2,14.5)
cup-=zcyl(-0.1,1.4,15.9,14.5)                                   # chamfer the inner lip
# cone up to the collar with 3 viewing windows
cone=zcyl(8,10,21,17)-zcyl(7.9,10.2,14.5,13.6)
for k in range(3):
    w=box(-5,10,9.5,10,14,6.5).rotate([0,0,90+120*k]); cone-=w
# bottle seat (45° funnel) : stops the bottle shoulder, lets the nozzle through (hole 15 mm)
seat=zcyl(12,6,13.6,13.6)-zcyl(11.9,6.2,7.5,13.6)
collar=zcyl(18,8,17)-zcyl(17.9,8.2,13.6)
# three spring fingers that grip bottles from 19 to 27 mm
fingers=None
for ang in (90,210,330):
    f=M.batch_hull([box(-3,12.4,26,6,1.4,0.5),box(-3,9.6,41.5,6,1.4,0.5)]).rotate([0,0,ang-90])
    fingers=f if fingers is None else fingers+f
# two squeeze wings (flex at their root) with inner pads and ribbed finger plates
wings=None
for s in (1,-1):
    arm=box(17 if s>0 else -19.2,-7,20,2.2,14,52)
    pad=box(14.3 if s>0 else -17.0,-5,44,2.75,10,12)
    plate=box(19.2 if s>0 else -21.4,-9,58,2.2,18,14)
    ribs=None
    for z in (60,63.5,67,70.5):
        r=box(21.4 if s>0 else -22.4,-9,z,1.0,18,1.4); ribs=r if ribs is None else ribs+r
    w=arm+pad+plate+ribs; wings=w if wings is None else wings+w
guide=cup+cone+seat+collar+fingers+wings
# size spacer ring for slim bottles (snaps into the collar, inner 19 mm)
spacer=zcyl(0,8,13.4)-zcyl(-0.1,8.2,9.6)
spacer-=box(-1,-14,-0.1,2,6,8.3)                                 # split so it squeezes in
def tm(m): me=m.to_mesh(); return trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts)
for n,m in {"eye_drop_guide":guide,"slim_bottle_spacer":spacer}.items():
    t=tm(m); t.export(OUT+n+".stl"); print(n,[round(float(v),1) for v in t.extents],"genus",m.genus(),"vol %.1f cm3"%(m.volume()/1000))
