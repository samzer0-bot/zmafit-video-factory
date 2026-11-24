import numpy as np, math, trimesh
from manifold3d import Manifold as M, CrossSection as CS
OUT="/home/user/zmafit-video-factory/sanad-stl/"; R=15.0
def align(m, p, t):
    t=np.array(t,float); t/=np.linalg.norm(t); z=np.array([0,0,1.0]); v=np.cross(z,t); s=np.linalg.norm(v); c=z@t
    if s<1e-9: Rm=np.eye(3) if c>0 else np.diag([1,-1,-1.0])
    else:
        K=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]]); Rm=np.eye(3)+K+K@K*((1-c)/s**2)
    return m.transform(np.c_[Rm,np.array(p,float)])
def disc(p,t): return align(M.cylinder(0.02,R,R,72).translate([0,0,-0.01]),p,t)
def P(x,z): return np.array([x,0.0,z])
def shaft(z0,z1): return [(P(300,z0),(0,0,1)),(P(300,z1),(0,0,1))]
B=[np.array(v,float) for v in [(300,435),(300,600),(0,600),(0,435)]]
def bez(t):
    a=(1-t)**3*B[0]+3*(1-t)**2*t*B[1]+3*(1-t)*t**2*B[2]+t**3*B[3]
    d=3*(1-t)**2*(B[1]-B[0])+6*(1-t)*t*(B[2]-B[1])+3*t**2*(B[3]-B[2])
    return P(*a),(d[0],0,d[1])
from manifold3d import Mesh as MM
def tube(samples, seg=72):
    V=[];F=[]
    for p,t in samples:
        t=np.array(t,float); t/=np.linalg.norm(t); y=np.array([0,1.0,0]); n=np.cross(y,t)
        for k in range(seg):
            a=2*math.pi*k/seg; V.append(p+R*(math.cos(a)*n+math.sin(a)*y))
    N=len(samples)
    for i in range(N-1):
        for k in range(seg):
            a=i*seg+k; b=i*seg+(k+1)%seg; c=a+seg; d=b+seg
            F+= [[a,b,d],[a,d,c]]
    c0=len(V); V.append(samples[0][0]); c1=len(V); V.append(samples[-1][0])
    for k in range(seg):
        F.append([c0,(k+1)%seg,k]); a=(N-1)*seg
        F.append([c1,a+k,a+(k+1)%seg])
    tm=trimesh.Trimesh(np.array(V),np.array(F),process=False)
    if tm.volume<0: tm.invert()
    return M(MM(vert_properties=np.asarray(tm.vertices,np.float32),tri_verts=np.asarray(tm.faces,np.uint32)))
def curve(t0,t1,n=40): return [bez(t0+(t1-t0)*i/n) for i in range(n+1)]
def rod(p0,p1,r):  # round-ended bar
    return M.batch_hull([M.sphere(r,48).translate(p0),M.sphere(r,48).translate(p1)])
def peg(base,direction,stem=22):
    d=np.array(direction,float); b=np.array(base,float)
    return rod(b,b+d*stem,8)+align(M.cylinder(10,5.8,5.8,48),b+d*stem,d)
# threads (eccentric helix, 3 mm pitch)
def thread(r,h):
    cs=CS.circle(r,64).translate([1.0,0])
    return M.extrude(cs,h,int(h*8),-h/3*360)
MALE=thread(9.0,18); FEMALE=thread(9.4,19.5).translate([0,0,-0.5])
pieces={
 "p1_bottom":  tube(shaft(15,165))+M.sphere(20,64).translate(P(300,10))+rod(P(300,90),P(188,90),11),
 "p2_middle":  tube(shaft(165,315))+rod(P(300,225),P(412,225),11)+peg(P(300,285),(1,0,0))+peg(P(300,180),(-1,0,0)),
 "p3_upper":   tube(shaft(315,435)),
 "p4_curve_a": tube(curve(0,0.5)),
 "p5_curve_b": tube(curve(0.5,1)),
 "p6_hook":    tube([(P(0,435),(0,0,-1)),(P(0,352),(0,0,-1))])+M.sphere(20,64).translate(P(0,334)),
}
pk,tk=bez(0.4); nk=np.array([-tk[2],0,tk[0]]); nk=nk/np.linalg.norm(nk)
if nk[2]<0: nk=-nk
pieces["p4_curve_a"]+=peg(pk+nk*(R-4),nk,16)
joints=[("p1_bottom","p2_middle",P(300,165),(0,0,1)),("p2_middle","p3_upper",P(300,315),(0,0,1)),
        ("p3_upper","p4_curve_a",*bez(0)),("p4_curve_a","p5_curve_b",*bez(0.5)),
        ("p5_curve_b","p6_hook",P(0,435),(0,0,-1))]
for a,b,p,t in joints:
    pieces[a]=pieces[a]+align(MALE,p,t); pieces[b]=pieces[b]-align(FEMALE,p,t)
# heads (fit on 5.8 mm pegs, 6.2 mm hole)
hole=M.cylinder(10.5,6.2,6.2,48).translate([0,0,-0.01])
heads={
 "head_round":  M.sphere(14,64).translate([0,0,10])+M.cylinder(10,10,10,48)-hole,
 "head_point":  M.batch_hull([M.cylinder(1,12,12,48),M.sphere(5,32).translate([0,0,30])])-hole,
 "head_double": M.batch_hull([M.cylinder(1,10,10,48),M.sphere(9,48).translate([-9,0,16]),M.sphere(9,48).translate([9,0,16])])-hole,
}
def mesh(m):
    me=m.to_mesh(); t=trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts); t.merge_vertices(); return t
asm=[]; total=0
for name,m in pieces.items():
    tm=mesh(m); asm.append(tm); total+=m.volume()
    flat=mesh(m.rotate([90,0,0])); flat.apply_translation(-flat.bounds[0]); flat.export(OUT+name+".stl")
    ex=flat.extents; print(f"{name}: {ex[0]:.0f} x {ex[1]:.0f} x {ex[2]:.0f} mm, watertight={tm.is_watertight}")
mounts=[(P(300,285)+np.array([32,0,0]),(1,0,0),"head_round"),(P(300,180)+np.array([-32,0,0]),(-1,0,0),"head_point"),(pk+nk*(R-4+16+2),nk,"head_double")]
for base,d,h in mounts:
    hm=heads[h]; total+=hm.volume(); asm.append(mesh(align(hm,base,d)))
for h,hm in heads.items(): mesh(hm).export(OUT+h+".stl")
A=trimesh.util.concatenate(asm); A.export(OUT+"sanad_assembled_preview.stl")
print("assembled extents mm:",[round(v) for v in A.extents], " solid volume cm3=%.0f"%(total/1000))
