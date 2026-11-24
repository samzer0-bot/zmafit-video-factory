import bpy, math, os, sys
P=os.path.abspath('bparts')
OUT='/home/user/zmafit-video-factory/dwaya-counter-blender/dwaya_counter_mechanism.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.unit_settings.system='METRIC'; sc.unit_settings.scale_length=0.001; sc.unit_settings.length_unit='MILLIMETERS'
def imp(name):
    f=os.path.join(P,name+'.stl')
    try: bpy.ops.wm.stl_import(filepath=f)
    except Exception: bpy.ops.import_mesh.stl(filepath=f)
    o=bpy.context.selected_objects[0]; o.name=name; return o
def mat(name,rgb,alpha=1.0,rough=.45):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(*rgb,1); b.inputs['Roughness'].default_value=rough; b.inputs['Alpha'].default_value=alpha
    m.blend_method='BLEND' if alpha<1 else 'OPAQUE'; return m
def empty(name,loc,parent=None):
    e=bpy.data.objects.new(name,None); e.empty_display_size=6; e.location=loc; sc.collection.objects.link(e)
    if parent: e.parent=parent; e.location=(loc[0]-parent.location[0],loc[1]-parent.location[1],loc[2]-parent.location[2])
    return e
def parent_keep(child,par):
    bpy.context.view_layer.update()
    w=child.matrix_world.copy(); child.parent=par; child.matrix_parent_inverse=par.matrix_world.inverted(); child.matrix_world=w
TEAL=(0.03,0.42,0.36); WHITE=(0.92,0.95,0.94); YEL=(0.98,0.78,0.25); ORANGE=(0.85,0.42,0.10)
body=imp('body'); body.data.materials.append(mat('Body',WHITE,0.18))
deck=imp('deck'); deck.data.materials.append(mat('Deck',(0.80,0.88,0.86),0.22))
plunger=imp('plunger'); plunger.data.materials.append(mat('Plunger',TEAL))
pawl=imp('pawl'); pawl.data.materials.append(mat('Pawl',(0.05,0.55,0.48)))
spring=imp('spring'); spring.data.materials.append(mat('Spring',(0.05,0.55,0.48)))
detent=imp('detent'); detent.data.materials.append(mat('Detent',(0.55,0.62,0.60)))
disc=imp('disc')
dm=bpy.data.materials.new('Disc'); dm.use_nodes=True; nt=dm.node_tree; b=nt.nodes['Principled BSDF']
tc=nt.nodes.new('ShaderNodeTexCoord'); sep=nt.nodes.new('ShaderNodeSeparateXYZ'); gt=nt.nodes.new('ShaderNodeMath'); gt.operation='GREATER_THAN'; gt.inputs[1].default_value=9.0
mix=nt.nodes.new('ShaderNodeMix'); mix.data_type='RGBA'
nt.links.new(tc.outputs['Object'],sep.inputs[0]); nt.links.new(sep.outputs['Z'],gt.inputs[0]); nt.links.new(gt.outputs[0],mix.inputs['Factor'])
mix.inputs['A'].default_value=(*YEL,1); mix.inputs['B'].default_value=(0.05,0.12,0.11,1)
nt.links.new(mix.outputs['Result'],b.inputs['Base Color']); b.inputs['Roughness'].default_value=.4
disc.data.materials.append(dm)
# medicine box
bpy.ops.mesh.primitive_cube_add(size=1); box=bpy.context.object; box.name='medicine_box'; box.scale=(56,30,110)
bpy.ops.object.transform_apply(scale=True); box.data.materials.append(mat('Box',ORANGE,1,.6))
BOXY,BOXZ=127.5-15,12+55
box.location=(35,BOXY,BOXZ)
# pivots
discpiv=empty('disc_pivot',(30,28,0)); parent_keep(disc,discpiv)
pawlpiv=empty('pawl_pivot',(55.4,44.3,0)); parent_keep(pawlpiv,plunger); parent_keep(pawl,pawlpiv)
detpiv=empty('detent_pivot',(4.6,8.5,0)); parent_keep(detent,detpiv)
sc.cursor.location=(37,99,0); bpy.ops.object.select_all(action='DESELECT'); spring.select_set(True); bpy.context.view_layer.objects.active=spring
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
# rest state = pushed (box inside)
STROKE=10.5; COMP=(99-80.5)/(99-70)
def k(obj,path,frame,val,idx=None):
    if idx is None: setattr(obj,path,val); obj.keyframe_insert(path,frame=frame)
    else:
        v=list(getattr(obj,path)); v[idx]=val; setattr(obj,path,v); obj.keyframe_insert(path,index=idx,frame=frame)
INTRO=12; CYC=48; N=4; END=INTRO+CYC*N+24
sc.frame_start=1; sc.frame_end=END; sc.render.fps=24
k(plunger,'location',1,STROKE,1); k(spring,'scale',1,COMP,1); k(box,'location',1,BOXZ,2); k(box,'location',1,BOXY,1)
k(discpiv,'rotation_euler',1,0,2); k(pawlpiv,'rotation_euler',1,0,2); k(detpiv,'rotation_euler',1,0,2)
for c in range(N):
    F=INTRO+CYC*c
    # removal
    k(box,'location',F+8,BOXZ,2); k(box,'location',F+20,BOXZ+140,2)
    k(box,'location',F+20,BOXY,1); k(box,'location',F+21,BOXY-12,1)
    k(plunger,'location',F+10,STROKE,1); k(plunger,'location',F+16,0,1)
    k(spring,'scale',F+10,COMP,1); k(spring,'scale',F+16,1.0,1)
    k(discpiv,'rotation_euler',F+10,math.radians(-22.5*c),2); k(discpiv,'rotation_euler',F+16,math.radians(-22.5*(c+1)),2)
    k(detpiv,'rotation_euler',F+10,0,2); k(detpiv,'rotation_euler',F+14,math.radians(7),2); k(detpiv,'rotation_euler',F+16,0,2)
    # return
    k(box,'location',F+28,BOXZ+140,2); k(box,'location',F+36,BOXZ,2); k(box,'location',F+36,BOXY-12,1); k(box,'location',F+44,BOXY,1)
    k(plunger,'location',F+37,0,1); k(plunger,'location',F+44,STROKE,1)
    k(spring,'scale',F+37,1.0,1); k(spring,'scale',F+44,COMP,1)
    k(pawlpiv,'rotation_euler',F+37,0,2); k(pawlpiv,'rotation_euler',F+41,math.radians(7),2); k(pawlpiv,'rotation_euler',F+44,0,2)
# make mechanical snaps linear
for ob in (plunger,spring,discpiv,pawlpiv,detpiv,box):
    if ob.animation_data:
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation='BEZIER' if ob is box else 'LINEAR'
# world, light, cameras
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.86,0.91,0.90,1); w.node_tree.nodes['Background'].inputs[1].default_value=0.9
sun=bpy.data.lights.new('Sun','SUN'); sun.energy=3.2; so=bpy.data.objects.new('Sun',sun); so.rotation_euler=(math.radians(40),math.radians(10),math.radians(30)); sc.collection.objects.link(so)
def cam(name,loc,target,lens):
    c=bpy.data.cameras.new(name); c.lens=lens; c.clip_start=1; c.clip_end=5000
    o=bpy.data.objects.new(name,c); o.location=loc; sc.collection.objects.link(o)
    t=empty(name+'_target',target); con=o.constraints.new('TRACK_TO'); con.target=t; con.track_axis='TRACK_NEGATIVE_Z'; con.up_axis='UP_Y'; return o
main=cam('Cam_Main',(175,-160,190),(36,58,14),42)
close=cam('Cam_Window',(30,-6,60),(30,11,9),70)
sc.camera=main
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=int(os.environ.get('SAMPLES','48'))
try: sc.cycles.use_denoising=False
except Exception: pass
sc.view_settings.view_transform='Standard'
sc.render.resolution_x=int(os.environ.get('RX','1080')); sc.render.resolution_y=int(os.environ.get('RY','1350'))
sc.render.film_transparent=False
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved",OUT,"frames",END)
