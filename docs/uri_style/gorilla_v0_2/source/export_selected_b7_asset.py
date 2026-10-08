"""Export the user's selected original gray B7 asset without recoloring it."""
from pathlib import Path
import sys
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'source/lower_modular_components_b7.blend'
original_sha=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
bpy.ops.object.select_all(action='DESELECT')
nodes=[o for o in bpy.context.scene.objects if o.name.startswith(('L_','R_')) and o.type in ('MESH','EMPTY')]
for o in nodes:o.select_set(True)
meshes=[o for o in nodes if o.type=='MESH']
bpy.context.view_layer.objects.active=meshes[0]
out=ROOT/'exports/lower_modular_components_b7.glb';out.parent.mkdir(exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,
                          export_yup=True,export_apply=False,export_materials='EXPORT',
                          export_cameras=False,export_lights=False,export_extras=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==original_sha
report={'source':'source/lower_modular_components_b7.blend','source_sha256':original_sha,
        'preview':'images/lower_modular_components_rear_oblique_b7.png',
        'glb':str(out.relative_to(ROOT)),'glb_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
        'mesh_object_count':len(meshes),'original_blend_unmodified':True,'original_gray_materials_retained':True,
        'joint_hierarchy_exported':True,'GLB_axis_convention':'+Y up; source +Z up converted by native Blender glTF exporter',
        'source_units':'Normalized appearance units; scale not a manufacturing dimension',
        'geometry_report':'lower_modular_components_b7.json','topology_or_physics_requalification_performed':False,
        'appearance_revision_separate_from_model':True,'whole_v0_2_qualified':False}
(ROOT/'selected_b7_asset_export.json').write_text(json.dumps(report,indent=2)+'\n')
print('ORIGINAL_SELECTED_B7_GLB_EXPORTED',len(meshes),flush=True)
