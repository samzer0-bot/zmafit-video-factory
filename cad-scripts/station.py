import math, numpy as np, trimesh
from manifold3d import Manifold as M, CrossSection as CS
OUT="/home/user/zmafit-video-factory/dwaya-station-stl/"
def box(x,y,z,dx,dy,dz): return M.cube([dx,dy,dz]).translate([x,y,z])
def ycyl(cx,cz,y0,h,r,seg=96): return M.cylinder(h,r,r,seg).rotate([-90,0,0]).translate([cx,y0,cz])
def zcyl(cx,cy,z0,h,r,seg=48): return M.cylinder(h,r,r,seg).translate([cx,cy,z0])
W,D=200,120
# ---------- row (front & back are identical) ----------
row=box(0,0,0,W,D,40)-box(4,4,4,W-8,D-8,40)          # tray, walls 4
row-=box(4,-1,18,W-8,6,30)                            # front lip lowered to 18 mm
for x in range(14,190,10): row-=box(x-1.7,6,2,3.4,D-12,2.1)   # divider grooves (pitch 10)
for (px,py) in [(20,20),(180,20),(20,100),(180,100)]: row-=zcyl(px,py,-0.01,3.01,4.2)  # stacking holes
fem=M.extrude(CS([[(0.1,-5.2),(0.1,5.2),(-4.2,7.2),(-4.2,-7.2)]]),36).translate([W,40,0])  # female dovetail, right side
row-=fem
# ---------- riser with drawer (sits behind the front row, carries the back row) ----------
RH=35
riser=box(0,0,0,W,D,RH)-box(4,4,-1,W-8,D-8,RH-3)       # open bottom, top 3 mm
riser-=box(W-5,10,4,6,D-20,RH-10)                      # drawer opening on right side
for (px,py) in [(20,20),(180,20),(20,100),(180,100)]: riser+=zcyl(px,py,RH,3,3.9)  # pegs
drawer=(box(6,12,5,W-12,D-24,RH-13)-box(8,14,7,W-16,D-28,RH-13))+box(W-6,30,8,8,D-60,14)  # tray + pull
# ---------- divider ----------
divider=box(0,0,0,3,D-14,48)
# ---------- clip-on time tags (sun / moon) ----------
def clip(): return box(0,0,0,18,10,3)+box(0,0,-14,18,2,14)+box(0,6,-6,18,2,6)   # hooks over 4-6 mm lip
sun=clip()+ycyl(9,-8,-3,3,6,48)
for k in range(8):
    a=2*math.pi*k/8; sun+=ycyl(9+7.6*math.cos(a),-8+7.6*math.sin(a),-3,3,2.2,24)
moon=clip()+(ycyl(9,-8,-3,3,7,48)-ycyl(12,-6,-3.1,3.2,6,48))
# ---------- dial tower ----------
TW,TD,TH=60,75,95; DC=(TW/2,55); R=22
tower=box(0,0,0,TW,TD,TH)-box(4,8,4,TW-8,TD-12,TH)
tower-=ycyl(*DC,-0.01,2.01,R+0.6); tower-=ycyl(*DC,0,7,3.5)
tower-=box(8,-0.01,10,TW-16,2.51,11)
tower+=M.extrude(CS([[(0,-5),(0,5),(-4,7),(-4,-7)]]),35).translate([0,40,0])   # male dovetail, left side
tower+=box(44,-4,80,5,4.01,6)+box(31,-4,82,14,4.01,1.6)+box(28.5,-4,80.5,3,4.01,1.6)  # pawl
dial=ycyl(*DC,-2,4,R)
for k in range(7):
    a=-math.pi/2+2*math.pi*k/7
    dial-=ycyl(DC[0]+R*math.cos(a),DC[1]-R*math.sin(a),-2.1,4.2,2.3,32)
dial+=ycyl(*DC,1.9,5.1,3.3)+box(DC[0]-1.2,-3.2,DC[1]-9,2.4,1.3,18)
slider=box(9,-1.5,10.4,20,4,10.2)
parts={"row_front":row,"row_back":row,"riser_with_drawer_slot":riser,"drawer":drawer,"divider":divider,
       "tag_sun":sun,"tag_moon":moon,"dial_tower":tower,"dial":dial,"slider":slider}
def mesh(m):
    me=m.to_mesh(); return trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts)
for n in ["row_front","riser_with_drawer_slot","drawer","divider","tag_sun","tag_moon","dial_tower","dial","slider"]:
    m=parts[n]; t=mesh(m)
    if n in("dial",): t=mesh(m.rotate([90,0,0]))
    if n=="divider": t=mesh(m.rotate([0,90,0]))
    t.apply_translation(-t.bounds[0]); t.export(OUT+("row" if n=="row_front" else n)+".stl")
    print(n, [round(v) for v in t.extents], "solid cm3=%.0f"%(m.volume()/1000), "genus",m.genus())
# assembly placement (world)
place={
 "row_front":(row,[0,0,0]), "riser":(riser,[0,D,0]), "drawer":(drawer,[0,D,0]), "row_back":(row,[0,D,RH]),
 "tower":(tower+dial+slider,[W+4,0,0]),
}
import json; asm=[]
for k,(m,o) in place.items(): asm.append(mesh(m.translate(o)))
divs=[]
for base,xs in [([0,0,0],[44,84,114,144,174]),([0,D,RH],[54,94,134,164])]:
    for x in xs: asm.append(mesh(divider.translate([x-1.5,base[1]+7,base[2]+2])))
for i,x in enumerate([20,60,95,125,155]):
    asm.append(mesh((sun if i%2==0 else moon).translate([x,-6,18])))
trimesh.util.concatenate(asm).export(OUT+"station_assembled_preview.stl")
