"""Blender appearance blockout and orthographic underlays, not engineering CAD.

Run with Blender --background --python this_file.py -- --output <folder>.
Front is -Y, up is +Z. All cameras use the same unposed appearance assembly.
"""
from pathlib import Path
import argparse
import json
import math
import sys

import bpy
from mathutils import Vector


parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
parser.add_argument("--resolution", type=int, default=1200)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out = Path(args.output).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0


def material(name, rgb, metallic=0.0, roughness=0.38):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


ivory = material("warm_ivory", (0.83, 0.80, 0.69))
blue = material("azure", (0.075, 0.36, 0.65), 0.05)
orange = material("saffron_release", (0.95, 0.48, 0.025))
metal = material("working_silver", (0.31, 0.36, 0.40), 0.65)
dark = material("joint_graphite", (0.045, 0.055, 0.065), 0.15)
glass = material("perception_glass", (0.015, 0.05, 0.075), 0.3, 0.15)
objects = []


def finish(obj, name, mat, bevel=0.025):
    obj.name = name
    obj.data.materials.append(mat)
    obj.data.use_auto_smooth = True
    if bevel:
        mod = obj.modifiers.new("appearance_radius", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = "ANGLE"
        normals = obj.modifiers.new("weighted_normals", "WEIGHTED_NORMAL")
        normals.keep_sharp = True
    objects.append(obj)
    return obj


def box(name, center, dims, mat, bevel=0.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, bevel)


def cylinder(name, center, radius, depth, mat, axis="X"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius,
                                      depth=depth, location=center)
    obj = bpy.context.object
    if axis == "X":
        obj.rotation_euler[1] = math.pi / 2
    elif axis == "Y":
        obj.rotation_euler[0] = math.pi / 2
    return finish(obj, name, mat, 0.01)


def profile(name, rings, mat, bevel=0.025):
    """Closed eight-sided transverse rings: z, half-width, front-y, rear-y."""
    verts = []
    for z, w, front, rear in rings:
        cut = (rear - front) * 0.18
        verts.extend([(-0.76*w, front, z), (0.76*w, front, z),
                      (w, front+cut, z), (w, rear-cut, z),
                      (0.76*w, rear, z), (-0.76*w, rear, z),
                      (-w, rear-cut, z), (-w, front+cut, z)])
    faces = [tuple(reversed(range(8)))]
    for j in range(len(rings)-1):
        faces.extend([(8*j+i, 8*j+(i+1)%8, 8*(j+1)+(i+1)%8, 8*(j+1)+i)
                      for i in range(8)])
    faces.append(tuple(range(len(verts)-8, len(verts))))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return finish(obj, name, mat, bevel)


def link_cover(name, a, b, width, depth, mat):
    a, b = Vector(a), Vector(b)
    obj = box(name, (a+b)/2, (width, depth, (b-a).length), mat, min(width, depth)*.30)
    obj.rotation_euler = (b-a).to_track_quat("Z", "Y").to_euler()
    return obj


# Broad, fuller shared head/torso. The frontal hood does not project into a snout.
core = profile("continuous_upper_core", [
    (1.74, .36, -.35, .28),
    (1.88, .51, -.43, .41),
    (2.17, .61, -.48, .49),
    (2.43, .62, -.38, .48),
    (2.60, .54, -.16, .40),
], ivory, .065)
smooth = core.modifiers.new("broad_continuous_shell", "SUBSURF")
smooth.levels = 2
smooth.render_levels = 2
for polygon in core.data.polygons:
    polygon.use_smooth = True

# Azure roof is broad all the way to the brow; no triangular shark-like nose.
sections = [(-.53, 2.34, .49), (-.51, 2.43, .54),
            (-.26, 2.60, .60), (.07, 2.66, .58),
            (.34, 2.61, .52), (.46, 2.46, .42)]
verts = []
for y, z, w in sections:
    for t in [-1, -.66, -.33, 0, .33, .66, 1]:
        verts.append((t*w, y, z-.075*t*t))
    for t in [1, .66, .33, 0, -.33, -.66, -1]:
        verts.append((t*w, y, z-.065-.075*t*t))
faces = [tuple(reversed(range(14)))]
for j in range(len(sections)-1):
    for i in range(14):
        faces.append((14*j+i, 14*j+(i+1)%14, 14*(j+1)+(i+1)%14, 14*(j+1)+i))
faces.append(tuple(range(len(verts)-14, len(verts))))
mesh = bpy.data.meshes.new("continuous_azure_roof")
mesh.from_pydata(verts, [], faces)
mesh.update()
obj = bpy.data.objects.new("continuous_azure_roof", mesh)
scene.collection.objects.link(obj)
finish(obj, "continuous_azure_roof", blue, .025)
smooth = obj.modifiers.new("continuous_hood_curve", "SUBSURF")
smooth.levels = 2
smooth.render_levels = 2
for polygon in obj.data.polygons:
    polygon.use_smooth = True
box("integrated_perception_band", (0, -.496, 2.295), (.72, .035, .095), glass, .025)
for x in [-.24, 0, .24]:
    cylinder("optical_window", (x, -.52, 2.295), .025, .018, metal, "Y")
box("front_release_marker", (0, -.464, 1.945), (.055, .018, .15), orange, .012)
box("dorsal_service_cover", (0, .491, 2.20), (.65, .065, .65), blue, .045)
for x in [-.24, .24]:
    box("dorsal_release", (x, .53, 2.29), (.045, .03, .14), orange, .012)
box("short_waist", (0, 0, 1.63), (.52, .44, .21), dark, .025)
profile("pelvis_shell", [(1.37, .27, -.24, .26),
                         (1.49, .46, -.30, .28),
                         (1.62, .45, -.28, .28)], blue, .035)
box("pelvis_service_cover", (0, -.305, 1.465), (.18, .05, .18), ivory, .025)
box("pelvis_release", (0, -.336, 1.47), (.065, .02, .095), orange, .008)

for side, sign in [("left", 1), ("right", -1)]:
    shoulder = (sign*.72, .04, 2.36)
    elbow = (sign*.87, -.015, 1.87)
    wrist = (sign*.99, -.085, 1.28)
    hip = (sign*.39, .015, 1.46)
    knee = (sign*.43, -.065, .91)
    ankle = (sign*.46, .01, .31)
    cylinder(side+"_shoulder_yoke", shoulder, .185, .22, dark)
    cylinder(side+"_shoulder_bearing", (sign*.835,.04,2.36), .15, .055, metal)
    guard = box(side+"_shoulder_guard", (sign*.80, .025, 2.45),
                (.40,.50,.37), ivory, .11)
    guard.rotation_euler[1] = -sign*.12
    box(side+"_shoulder_blue", (sign*.90,.08,2.565), (.16,.25,.065),blue,.028)
    link_cover(side+"_upper_arm", shoulder, elbow, .29, .33, ivory)
    cylinder(side+"_elbow", elbow, .14, .36, dark)
    cylinder(side+"_elbow_cap", (sign*.105+elbow[0],elbow[1],elbow[2]), .115, .1, metal)
    link_cover(side+"_forearm", (sign*.89,-.025,1.78), (sign*.98,-.077,1.38),
               .38, .37, ivory)
    link_cover(side+"_forearm_blue", (sign*1.07,-.045,1.77),
               (sign*1.13,-.077,1.39), .12,.32, blue)
    cylinder(side+"_wrist", wrist, .108,.19,dark,"Z")
    cylinder(side+"_tool_release", (wrist[0],wrist[1],1.35),.12,.07,orange,"Z")
    box(side+"_palm", (sign*.99,-.09,1.15), (.26,.18,.23),ivory,.035)
    box(side+"_palm_pad", (sign*.99,-.189,1.14), (.20,.02,.17),dark,.015)
    for i in range(3):
        x=sign*.99+(i-1)*.078
        box(side+f"_finger_{i}_proximal", (x,-.115, .985),(.068,.095,.17),dark,.018)
        box(side+f"_finger_{i}_tip", (x,-.15,.89),(.068,.10,.095),metal,.018)
    box(side+"_thumb", (sign*.82,-.105,1.08),(.08,.115,.15),dark,.025)
    cylinder(side+"_hip_bearing", hip,.185,.25,dark)
    link_cover(side+"_thigh", (sign*.39,.015,1.43), (sign*.43,-.065,1.00),
               .40,.43,ivory)
    cylinder(side+"_knee", knee,.155,.47,dark)
    cylinder(side+"_knee_silver", (sign*.655,-.065,.91),.125,.08,metal)
    box(side+"_knee_blue", (sign*.43,-.298,.93),(.28,.10,.25),blue,.035)
    box(side+"_knee_release", (sign*.43,-.343,.81),(.10,.025,.065),orange,.012)
    link_cover(side+"_calf", (sign*.435,-.05,.78), (sign*.46,.01,.38),.39,.40,ivory)
    cylinder(side+"_ankle", ankle,.12,.38,dark)
    cylinder(side+"_ankle_cap", (sign*.65,.01,.31),.10,.04,metal)
    box(side+"_sole", (sign*.46,-.12,.073),(.43,.63,.146),dark,.035)
    shoe=box(side+"_foot_shell", (sign*.46,-.13,.19),(.44,.59,.19),ivory,.085)
    box(side+"_toe_blue", (sign*.46,-.375,.16),(.40,.13,.18),blue,.025)
    box(side+"_foot_crown_blue", (sign*.46,-.16,.28),(.20,.42,.09),blue,.025)

# Normalize whole appearance assembly to the selected art-scale, without changing ratios.
bpy.context.view_layer.update()
points = [o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
min_z=min(v.z for v in points); max_z=max(v.z for v in points)
scale=2.65/(max_z-min_z)
for obj in objects:
    obj.location.z-=min_z
    obj.location*=scale
    obj.scale*=scale
bpy.context.view_layer.update()
points=[o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
bounds={axis:[min(getattr(v,axis) for v in points),max(getattr(v,axis) for v in points)]
        for axis in "xyz"}

world=bpy.data.worlds.new("paper_studio")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs[0].default_value=(.85,.89,.95,1)
world.node_tree.nodes["Background"].inputs[1].default_value=.4
scene.world=world
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=32
scene.cycles.use_denoising=False
scene.render.threads_mode="FIXED"
scene.render.threads=8
scene.render.resolution_x=args.resolution
scene.render.resolution_y=args.resolution
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.film_transparent=False
scene.view_settings.view_transform="Standard"
scene.view_settings.look="Medium High Contrast"


def point_at(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


for name,location,power,size in [
    ("large_key",(-3,-5,6),300,5),
    ("large_fill",(4,-1,4),200,5),
    ("rear_fill",(0,5,5),300,4),
]:
    data=bpy.data.lights.new(name,"AREA");data.energy=power;data.shape="DISK";data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    obj.location=location;point_at(obj,(0,0,1.3))
data=bpy.data.cameras.new("appearance_orthographic")
camera=bpy.data.objects.new("appearance_orthographic",data)
scene.collection.objects.link(camera);scene.camera=camera;data.type="ORTHO";data.ortho_scale=3.12
view_records=[]
views={"front":((0,-9,1.325),(0,0,1.325)),
       "left":((9,0,1.325),(0,0,1.325)),
       "rear":((0,9,1.325),(0,0,1.325)),
       "top":((0,0,10),(0,0,0)),
       "front_three_quarter":((5,-8,3.5),(0,0,1.325)),
       "rear_three_quarter":((5,8,3.5),(0,0,1.325))}
for name,(location,target) in views.items():
    camera.location=location;point_at(camera,target)
    if name=="top":camera.rotation_euler=(0,0,0)
    scene.render.filepath=str(out/f"{name}.png")
    print("VIEW",name,flush=True)
    bpy.ops.render.render(write_still=True)
    view_records.append({"name":name,"camera_location":list(camera.location),
                         "camera_rotation":list(camera.rotation_euler),
                         "projection":"ORTHO","ortho_scale_m":data.ortho_scale})
camera.location=views["front_three_quarter"][0]
point_at(camera,views["front_three_quarter"][1])
bpy.ops.wm.save_as_mainfile(filepath=str(out.parent/"gorilla_appearance_blockout.blend"))

# Build the contact sheet natively in Blender from the actual camera renders.
board=bpy.data.scenes.new("orthographic_appearance_sheet")
board.render.engine="CYCLES";board.cycles.samples=1
board.cycles.use_denoising=False
board.render.resolution_x=2400;board.render.resolution_y=2400
board.render.resolution_percentage=100
board.render.image_settings.file_format="PNG"
board.view_settings.view_transform="Standard"
board.world=world
for label,xy in [("front",(-1.55,1.60)),("left",(1.55,1.60)),
                 ("rear",(-1.55,-1.58)),("top",(1.55,-1.58))]:
    img=bpy.data.images.load(str(out/f"{label}.png"))
    mesh=bpy.data.meshes.new(label+"_sheet_plane")
    x,y=xy;h=1.45
    mesh.from_pydata([(x-h,y-h,0),(x+h,y-h,0),(x+h,y+h,0),(x-h,y+h,0)],[],[(0,1,2,3)])
    mesh.uv_layers.new()
    for poly in mesh.polygons:
        for i,uv in zip(poly.loop_indices,[(0,0),(1,0),(1,1),(0,1)]):mesh.uv_layers[0].data[i].uv=uv
    obj=bpy.data.objects.new(label+"_sheet_plane",mesh);board.collection.objects.link(obj)
    mat=bpy.data.materials.new(label+"_sheet_image");mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear()
    tex=nodes.new("ShaderNodeTexImage");tex.image=img
    emit=nodes.new("ShaderNodeEmission");output=nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(tex.outputs["Color"],emit.inputs["Color"])
    mat.node_tree.links.new(emit.outputs[0],output.inputs["Surface"])
    obj.data.materials.append(mat)
    font=bpy.data.curves.new(label+"_label","FONT")
    font.body=label.upper();font.align_x="CENTER";font.size=.09
    title=bpy.data.objects.new(label+"_label",font);title.location=(x,y-h-.08,.01)
    board.collection.objects.link(title)
    textmat=bpy.data.materials.new(label+"_label_material");textmat.use_nodes=True
    nt=textmat.node_tree;nt.nodes.clear()
    em=nt.nodes.new("ShaderNodeEmission");em.inputs[0].default_value=(.03,.05,.08,1)
    output=nt.nodes.new("ShaderNodeOutputMaterial");nt.links.new(em.outputs[0],output.inputs["Surface"])
    title.data.materials.append(textmat)
camdata=bpy.data.cameras.new("sheet_orthographic");camdata.type="ORTHO";camdata.ortho_scale=6.6
cam=bpy.data.objects.new("sheet_orthographic",camdata);board.collection.objects.link(cam)
cam.location=(0,0,10);cam.rotation_euler=(0,0,0);board.camera=cam
board.render.filepath=str(out/"orthographic_sheet.png")
bpy.ops.render.render(write_still=True,scene=board.name)
bpy.ops.wm.save_as_mainfile(filepath=str(out.parent/"gorilla_appearance_blockout.blend"))
(out.parent/"blockout_manifest.json").write_text(json.dumps({
    "name":"Gorilla V0.1","revision":"C","blender":bpy.app.version_string,
    "scope":"appearance-envelope blockout only; no engineered geometry or physics",
    "orientation":{"front":"-Y","up":"+Z"},"unit":"metre",
    "height_intent_m":2.65,"assembly_bounds_m":bounds,
    "object_count":len(objects),"same_assembly_for_all_views":True,
    "changes":"fuller central torso, broad roof and reduced forward snout; subtle gorilla forearms",
    "views":view_records,
},ensure_ascii=False,indent=2)+"\n")
print("BLOCKOUT_COMPLETE",flush=True)
