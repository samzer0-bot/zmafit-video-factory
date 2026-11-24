# Dwaya once-a-day slot, 30 days: units driver (20 teeth, 9..0 twice) + tens star (16 slots, 3..0) carried every 10 doses
import math, numpy as np, trimesh, sys
from manifold3d import Manifold as M, CrossSection as CS, FillRule
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
OUT="/home/user/zmafit-video-factory/dwaya-counter30-stl/"
def box(x,y,z,dx,dy,dz): return M.cube([dx,dy,dz]).translate([x,y,z])
def zcyl(x,y,z,h,r,seg=64): return M.cylinder(h,r,r,seg).translate([x,y,z])
def ccw(p):
    a=sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))); return p if a>0 else p[::-1]
def prism(p,z0,h): return M.extrude(CS([ccw(p)]),h).translate([0,0,z0])
fp=FontProperties(family="DejaVu Sans",weight="bold")
def label(txt,size,cx,cy,rot,z,h=0.6):
    tp=TextPath((0,0),txt,size=size,prop=fp); polys=[p for p in tp.to_polygons() if len(p)>2]
    allp=np.vstack(polys); c=(allp.min(0)+allp.max(0))/2
    cs=CS([[(float(x-c[0]),float(y-c[1])) for x,y in p] for p in polys],FillRule.EvenOdd).rotate(rot).translate([cx,cy])
    return M.extrude(cs,h).translate([0,0,z])
# ---- layout ----
W,D=103,140
C1=(65.2,28.0); RT,RR=24,21; N1=20; S1=360/N1           # units driver
DST=40.0; RP=22.5                                         # star distance, pin radius
C2=(C1[0]-DST,C1[1]); RS=19.2; NS=16; SS=360/NS           # day star
Z0,Z1=2.2,8.2; DZ0,DZ1=2.8,8.8; SZ0,SZ1=9.6,13.6; DECKZ=14
STROKE=10.5; dx=C1[0]-30
# ---- body ----
body=box(0,0,0,W,D,2)+box(0,0,0,3,D,64)+box(W-3,0,0,3,D,64)+box(0,D-4,0,W,4,64)+box(0,0,0,W,3,DECKZ)
body+=box(3,3,DECKZ-2,2,113,2)+box(W-5,3,DECKZ-2,2,113,2)
body+=box(62.4+dx,30,2,W-3-(62.4+dx),90,6)                               # outer guide rail
body+=zcyl(*C1,2,7.5,3.0)+zcyl(*C1,2,0.6,6)                               # driver axle
body+=zcyl(*C2,2,SZ0-2-0.2,5.0)+zcyl(*C2,2,SZ1-2-0.2,3.0)                 # star axle + spacer
body+=box(22+dx,100,2,30,4,8)+box(56.5+dx,35,2,5.5,4.6,6)                 # spring post, rest stop
body+=box(10,130.8,2,8,5.2,30)+box(W-18,130.8,2,8,5.2,30)                 # push stops
# driver anti-reverse detent (left of driver, below star level)
body+=box(2.5+dx,4,2,4,6,6.2)+box(4.0+dx,8,2,1.2,15.0,6.2)
body+=prism([(4.6+dx,24.0),(8.2+dx,24.0),(4.6+dx,18.9)],2,6.2)
# star detent (flexure from back, bump into a slot at angle 168.75)
a=math.radians(168.75); bx=C2[0]+RS*math.cos(a); by=C2[1]+RS*math.sin(a)
body+=box(3,by+12,SZ0,4,4,SZ1-SZ0)+box(bx-2.6,by,SZ0,1.2,14,SZ1-SZ0)
body+=prism([(bx-1.4,by-1.6),(bx+1.6,by),(bx-1.4,by+1.6)],SZ0,SZ1-SZ0)
# ---- phase driver ----
pts=[]
for k in range(N1):
    a=-9+k*S1
    pts.append((C1[0]+RR*math.cos(math.radians(a)),C1[1]+RR*math.sin(math.radians(a))))
    b=math.radians(a+S1-0.6); pts.append((C1[0]+RT*math.cos(b),C1[1]+RT*math.sin(b)))
drv=M.extrude(CS([ccw(pts)]),DZ1-DZ0).translate([0,0,DZ0])-zcyl(*C1,DZ0-0.1,10,3.25)
WU=-135                                                                    # units window angle
for i in range(N1):
    phi=WU+i*S1
    drv+=label(str((0-i)%10),4.6,C1[0]+13*math.cos(math.radians(phi)),C1[1]+13*math.sin(math.radians(phi)),phi-WU,DZ1)
for ang in (189,9):                                                         # carry pins: 0 -> 9 transition
    drv+=zcyl(C1[0]+RP*math.cos(math.radians(ang)),C1[1]+RP*math.sin(math.radians(ang)),DZ1,SZ1-0.2-DZ1,1.8,24)
# ---- day star ----
star=zcyl(*C2,SZ0,SZ1-SZ0,RS,96)-zcyl(*C2,SZ0-0.1,6,3.25)
for k in range(NS):
    a=math.radians(-11.25+k*SS); L=6.5
    sl=box(0,-2.3,-0.1,L+2,4.6,SZ1-SZ0+0.2)+zcyl(0,0,-0.1,SZ1-SZ0+0.2,2.3,24)
    star-=sl.rotate([0,0,math.degrees(a)]).translate([C2[0]+(RS-L)*math.cos(a),C2[1]+(RS-L)*math.sin(a),SZ0])
WT=-45                                                                     # tens window angle
for i in range(NS):
    phi=WT-i*SS; v=(3-i)%4
    star+=label(str(v),4.6,C2[0]+9.8*math.cos(math.radians(phi)),C2[1]+9.8*math.sin(math.radians(phi)),phi-WT,SZ1)
# ---- plunger (rest) ----
pl =box(56+dx,40,Z0,6,80,Z1-Z0)+box(8,117,Z0,W-16,3,58-Z0)+box(22+dx,66,Z0,34,4,Z1-Z0)
pl-=box(55.9+dx,87.7,4.2,6.2,3.6,5)
pl+=box(54.8+dx,26,Z0,1.2,18.5,Z1-Z0)
pl+=prism([(51.8+dx,23.9),(56.0+dx,23.9),(56.0+dx,30.0),(54.8+dx,30.0)],Z0,Z1-Z0)
zz=[(37+dx,70.0)]; ys=np.linspace(70,99.0,8)
for i,y in enumerate(ys[1:-1]): zz.append(((25 if i%2==0 else 49)+dx,float(y)))
zz.append((37+dx,99.0)); spring=None
for (x0,y0),(x1,y1) in zip(zz,zz[1:]):
    s=M.batch_hull([zcyl(x0,y0,Z0,Z1-Z0,0.65,16),zcyl(x1,y1,Z0,Z1-Z0,0.65,16)]); spring=s if spring is None else spring+s
spring+=box(29+dx,98.6,Z0,16,0.6,Z1-Z0); pl+=spring
# ---- deck ----
deck=box(3.2,3.2,DECKZ,W-6.4,112.6,2)
ux=C1[0]+13*math.cos(math.radians(WU)); uy=C1[1]+13*math.sin(math.radians(WU))
deck-=box(ux-3.6,uy-4.2,DECKZ-0.1,7.2,8.4,2.2)                            # units window
tx=C2[0]+9.8*math.cos(math.radians(WT)); ty=C2[1]+9.8*math.sin(math.radians(WT))
deck-=box(tx-3.6,ty-4.2,DECKZ-0.1,7.2,8.4,2.2)                            # tens window
for k in range(2): deck+=zcyl(ux+7+k*0,uy+2-4*k,DECKZ+2,0.7,0.9,16)                  # tactile dots by the units window
deck+=zcyl(tx-7,ty,DECKZ+2,0.7,0.9,16)                                           # one tactile dot by the tens window
deck-=box(20,55.1,DECKZ+5,W-40,0.8,10)                                           # label-card slot in the front lip
deck-=box(57.3+dx,98.3,DECKZ-0.1,3.4,3.4,2.2)                             # pause pin hole
deck+=box(3.2,54,DECKZ+2,W-6.4,3,12)                                       # front lip
pin=box(0,0,0,3.0,3.0,DECKZ-4.5+0.1)+box(-2.5,-2.5,DECKZ-4.4,8,8,2.4)
parts={"body":body,"phase_driver":drv,"day_star":star,"plunger":pl,"deck":deck,"pause_pin":pin}
if __name__=="__main__":
    def tm(m): me=m.to_mesh(); return trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts)
    for n,m in parts.items():
        t=tm(m); t.apply_translation(-t.bounds[0]); t.export(OUT+n+".stl")
        print(f"{n}: {[round(float(v),1) for v in t.extents]} genus={m.genus()}")
    for nm,sh in (("rest",0),("pushed",STROKE)):
        p=pl.translate([0,sh,0])
        print(nm,"pl∩body %.1f pl∩drv %.1f pl∩star %.1f drv∩body %.1f star∩body %.1f drv∩star %.1f"%(
          (p^body).volume(),(p^drv).volume(),(p^star).volume(),(drv^body).volume(),(star^body).volume(),(drv^star).volume()))
    # kinematic check: pin polar angle about C2 at driver angles 190 / 170
    for ang in (189,180,171):
        px=C1[0]+RP*math.cos(math.radians(ang)); py=C1[1]+RP*math.sin(math.radians(ang))
        print("pin@",ang,"dist to star centre %.2f polar %.2f"%(math.hypot(px-C2[0],py-C2[1]),math.degrees(math.atan2(py-C2[1],px-C2[0]))))
