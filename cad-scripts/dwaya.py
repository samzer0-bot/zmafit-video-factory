import math, numpy as np, trimesh
from manifold3d import Manifold as M, CrossSection as CS
OUT="/home/user/zmafit-video-factory/dwaya-stl/"
def box(x,y,z,dx,dy,dz): return M.cube([dx,dy,dz]).translate([x,y,z])
def ycyl(cx,cz,y0,h,r,seg=96): return M.cylinder(h,r,r,seg).rotate([-90,0,0]).translate([cx,y0,cz])
W,D,H=130,75,85; DC=(65,50); R=30
# --- body ---
body=box(0,0,0,W,D,H)-box(5,8,5,120,62,81)
body-=ycyl(*DC,-0.01,2.01,R+0.6)            # dial recess
body-=ycyl(*DC,0,7,4.0)                       # axle hole
body-=box(20,-0.01,5,90,2.51,12)              # slider channel
for yy in (28,38,48,58): body-=box(5,yy,3,120,3.4,2.1)  # divider slots
# dovetail male (right) / female (left)
male=M.extrude(CS([[(0,-5),(4,-7),(4,7),(0,5)]]),75).translate([W,37.5,5])
fem =M.extrude(CS([[(-0.1,-5.2),(4.2,-7.2),(4.2,7.2),(-0.1,5.2)]]),76).translate([0,37.5,4.99])
body=body+male-fem
# compliant pawl (prints with body)
body+=box(90,-4,79,6,4.01,6)                  # anchor
body+=box(66,-4,81,25,4.01,1.6)               # flexure beam
body+=box(63.5,-4,80.0,3,4.01,1.6)            # tip
# --- dial ---
dial=ycyl(DC[0],DC[1],-2,4,R)
for k in range(7):
    a=-math.pi/2+2*math.pi*k/7
    dial-=ycyl(DC[0]+R*math.cos(a),DC[1]-R*math.sin(a),-2.1,4.2,2.6,32)
    dial+=ycyl(DC[0]+21*math.cos(a),DC[1]-21*math.sin(a),-2.8,0.9,2.2,32)   # day markers
dial+=ycyl(*DC,1.9,5.1,3.8)                   # axle pin
dial+=box(DC[0]-1.5,-3.2,DC[1]-12,3,1.3,24)   # finger ridge
# --- slider ---
slider=box(21,-1.5,5.4,44,4,11.2)+box(41,-2.6,7,4,1.2,8)
# --- divider ---
divider=box(6,38.2,3.1,118,3,64)
def save(m,name):
    me=m.to_mesh(); t=trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts)
    t.export(OUT+name); return t
parts={'body':body,'dial':dial,'slider':slider,'divider':divider}
asm=save(body+dial+slider+divider,"dwaya_module_assembled.stl")
save(body,"part1_body.stl")
save(dial.rotate([90,0,0]),"part2_day_dial.stl")
save(slider.rotate([90,0,0]),"part3_slider.stl")
save(divider.rotate([90,0,0]),"part4_divider.stl")
for n,m in parts.items():
    print(n, "volume cm3=%.1f"%(m.volume()/1000), "PLA g≈%.0f"%(m.volume()/1000*1.24))
print("watertight", asm.is_watertight, asm.bounds.tolist())
