import math, numpy as np, trimesh
from manifold3d import Manifold as M, CrossSection as CS, FillRule
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
OUT="/home/user/zmafit-video-factory/dwaya-counter-stl/"
def box(x,y,z,dx,dy,dz): return M.cube([dx,dy,dz]).translate([x,y,z])
def zcyl(x,y,z,h,r,seg=64): return M.cylinder(h,r,r,seg).translate([x,y,z])
def prism(pts,z0,h): return M.extrude(CS([pts]),h).translate([0,0,z0])
def ccw(pts):
    a=sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))
    return pts if a>0 else pts[::-1]
W,D=70,140; CX,CY=30,28; RT,RR=24,21; N=16; STEP=360/N
Z0,Z1=2.2,8.2            # plunger band
DZ0,DZ1=2.8,8.8          # disc band
STROKE=10.5
# ---------------- body ----------------
body=box(0,0,0,W,D,2)+box(0,0,0,3,D,60)+box(W-3,0,0,3,D,60)+box(0,D-4,0,W,4,60)+box(0,0,0,W,3,10)
body+=box(3,3,8,2,113,2)+box(W-5,3,8,2,113,2)                      # deck ledges (deck sits at z 10)
body+=box(62.4,30,2,W-3-62.4,90,6)                                   # outer guide rail for plunger bar
body+=zcyl(CX,CY,2,7.5,3.0)+zcyl(CX,CY,2,0.6,6)                      # axle peg + spacer
body+=box(22,100,2,30,4,8)                                           # spring stop post
body+=box(56.5,35,2,5.5,4.6,6)                                       # rest stop for bar
body+=box(10,130.8,2,8,5.2,30)+box(44,130.8,2,8,5.2,30)              # push stops for paddle
# anti-reverse detent (flexure + hook), anchored at front-left
body+=box(2.5,4,2,4,6,6.2)+box(4.0,8,2,1.2,15.3,6.2)
body+=prism(ccw([(4.6,23.0),(8.2,23.0),(4.6,17.9)]),2,6.2)
# ---------------- disc ----------------
saw2=[]
for k in range(N):
    a=-11.25+k*STEP
    saw2.append((RR*math.cos(math.radians(a)),RR*math.sin(math.radians(a))))          # root right after previous ramp
    saw2.append((RT*math.cos(math.radians(a+STEP-0.6)),RT*math.sin(math.radians(a+STEP-0.6))))  # ramp rises to tip just before next face
disc=M.extrude(CS([ccw(saw2)]),DZ1-DZ0).translate([CX,CY,DZ0])
disc-=zcyl(CX,CY,DZ0-0.1,10,3.25)
# digits (raised 0.6) : value v at angle -90+(15-v)*STEP, rotated so upright in window
fp=FontProperties(family="DejaVu Sans",weight="bold")
for v in range(16):
    tp=TextPath((0,0),str(v),size=6.2,prop=fp); polys=[p for p in tp.to_polygons() if len(p)>2]
    if not polys: continue
    allp=np.vstack(polys); c=(allp.min(0)+allp.max(0))/2
    cs=CS([[(float(x-c[0]),float(y-c[1])) for x,y in p] for p in polys],FillRule.EvenOdd)
    phi=-90+(15-v)*STEP
    cs=cs.rotate(phi+90).translate([CX+17*math.cos(math.radians(phi)),CY+17*math.sin(math.radians(phi))])
    disc+=M.extrude(cs,0.6).translate([0,0,DZ1])
# ---------------- plunger (rest position) ----------------
pl =box(56,40,Z0,6,80,Z1-Z0)                       # bar  y 40..120
pl+=box(8,117,Z0,54,3,55-Z0)                       # paddle y 117..120, up to z 55
pl+=box(54.8,26,Z0,1.2,18,Z1-Z0)                   # pawl flexure beam
pl+=prism(ccw([(51.8,23.2),(56.0,23.2),(56.0,29.5),(54.8,29.5)]),Z0,Z1-Z0)   # pawl hook: flat face -Y
pl+=box(22,66,Z0,34,4,Z1-Z0)                       # crossbar to spring
pl-=box(55.9,87.7,4.2,6.2,3.6,5)                   # pause-pin notch
# zig-zag spring from crossbar (y70) to stop post (y99.6)
zz=[(37,70.0)]; ys=np.linspace(70,99.0,8)
for i,y in enumerate(ys[1:-1]): zz.append((25 if i%2==0 else 49,float(y)))
zz.append((37,99.0))
for (x0,y0),(x1,y1) in zip(zz,zz[1:]):
    pl+=M.batch_hull([zcyl(x0,y0,Z0,Z1-Z0,0.65,16),zcyl(x1,y1,Z0,Z1-Z0,0.65,16)])
pl+=box(29,98.6,Z0,16,0.6,Z1-Z0)                   # end pad
# ---------------- deck ----------------
deck=box(3.2,3.2,10,W-6.4,112.6,2)
deck-=box(26.3,6,9.9,7.4,10,2.2)                    # number window
deck-=box(3.1,18,9.9,7,20,2.2)                     # finger notch to set the disc
deck-=box(57.3,98.3,9.9,3.4,3.4,2.2)               # pause-pin hole
deck+=box(3.2,50,12,W-6.4,3,12)                    # front lip: keeps the box off the window
# ---------------- pause pin ----------------
pin=box(0,0,0,3.0,3.0,8.0)+box(-2.5,-2.5,8.0,8,8,2.4)
parts={"body":body,"disc":disc,"plunger":pl,"deck":deck,"pause_pin":pin}
def tm(m):
    me=m.to_mesh(); return trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts)
for n,m in parts.items():
    t=tm(m); t.apply_translation(-t.bounds[0]); t.export(OUT+n+".stl")
    print(f"{n}: {[round(v,1) for v in t.extents]} genus={m.genus()} vol={m.volume()/1000:.1f}cm3")
# interference checks at rest and pushed
for name,shift in [("rest",0),("pushed",STROKE)]:
    p=pl.translate([0,shift,0])
    print(name,"plunger∩body=%.2f"%(p^body).volume(),"plunger∩disc=%.2f"%(p^disc).volume(),"disc∩body=%.2f"%(disc^body).volume())
