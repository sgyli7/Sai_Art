"""Hollow the existing authored bridge; retain exterior silhouette and transport.

Complete assembly plus authored interior parts, declared door openings and simple
fixture contact shapes. Closed doors are still transport geometry in this stage.
"""
from pathlib import Path
import copy,gzip,hashlib,json,math
import numpy as np
import trimesh as tm
from suspension_physics import ROOT
from mesh_profiles import extrude_xz
from export_assembly import export
OUT=ROOT/'candidates/r023_interior'
def box(c,s):
    m=tm.creation.box(s);m.apply_translation(c);return m
def prism_xy(points,z0,z1):return tm.convex.convex_hull([(x,y,z) for x,y in points for z in [z0,z1]])
def mesh(p):return tm.Trimesh(p['vertices'],p['faces'],process=False)
def main():
    src=ROOT/'candidates/r021_track_tension/source/assembly.json.gz';a=json.loads(gzip.decompress(src.read_bytes()));old=copy.deepcopy(a)
    v=json.loads((ROOT/'design/vehicle.json').read_text());c=v['bridge_interior_candidate'];f=c['floor_z'];modified=[];added=[];contacts=[];serial=0
    a['colors'].update(cabin_floor='465256',cabin_panel='a5b2a8',cabin_worktop='ac8c65',cabin_screen='182f32',cabin_light='efe8ce',cabin_glass='99bdc2')
    a['material_properties']={'cabin_glass':{'alpha':.22,'roughness':.14,'metallic':0.,'double_sided':True},'cabin_light':{'emissive':[.75,.69,.48]},'cabin_floor':{'roughness':.88,'metallic':0.},'cabin_worktop':{'roughness':.7,'metallic':0.}}
    def replace(p,m):
        assert m.is_volume,p['name'];p['vertices']=m.vertices.tolist();p['faces']=m.faces.tolist();modified.append(p['name'])
    def add(name,m,material='cabin_panel',contact=None,category='fixture'):
        nonlocal serial
        assert m.is_volume,name
        p=dict(name=f'r023_{serial:04d}_{name}',group='front',material=material,vertices=m.vertices.tolist(),faces=m.faces.tolist(),motion={'kind':'static'},assembly='bridge_interior',interior_category=category,physical_body='front')
        a['parts'].append(p);added.append(p['name']);serial+=1
        if contact:contacts.append(dict(name=p['name'],body='front',**contact))
        return p
    def cube(name,center,size,mat='cabin_panel',contact=False,category='fixture'):
        return add(name,box(center,size),mat,dict(type='box',center_source_m=center,size_m=size) if contact else None,category)
    def bolt(name,center,axis=(0,1,0),radius=.018):
        m=tm.creation.cylinder(radius=radius,height=.012,sections=6);m.apply_transform(tm.geometry.align_vectors([0,0,1],axis));m.apply_translation(center);return add(name,m,'steel')
    # Inner cavity obeys the existing sloped rear face and chamfered nose.
    plan=[(16.22,-3.30),(31.97,-3.30),(33.80,-2.705),(33.80,2.705),(31.97,3.30),(16.22,3.30)]
    inner=tm.boolean.intersection([prism_xy(plan,f-.025,c['ceiling_z']),extrude_xz([(16.22,f-.025),(33.8,f-.025),(33.8,c['ceiling_z']),(17.16,c['ceiling_z'])],0,6.6)],engine='manifold')
    cutters=[inner,box([31.45,0,10.38],[4.0,5.1,1.40])];doors=[]
    for side in [-1,1]:
        for x in v['bridge']['door_x']:
            cut=box([x,side*3.50,f+c['door_clear_height_m']/2],[c['door_clear_width_m'],1.15,c['door_clear_height_m']])
            cutters.append(cut);doors.append(dict(center_x=x,side=side,clear_width_m=c['door_clear_width_m'],clear_height_m=c['door_clear_height_m'],sill_z=f,state='closed transport leaf; aperture clear only with leaf open'))
            for p in a['parts']:
                if p['name'].endswith('bridge_door_gasket') and np.linalg.norm(mesh(p).centroid[:2]-[x,side*3.535])<.1:replace(p,tm.boolean.difference([mesh(p),cut],engine='manifold'))
    # Legacy gallery brackets protruded 42.5 mm above the walking surface;
    # seat them fully below it, and trim paint that crossed the new openings.
    door_tool=tm.boolean.union(cutters[2:],engine='manifold')
    for p in a['parts']:
        if p['name'].endswith('bridge_gallery_bracket'):
            m=mesh(p);m.apply_translation([0,0,-.05]);replace(p,m)
        if p['name'].endswith('paint_bridge_trim'):
            m=tm.boolean.difference([mesh(p),door_tool],engine='manifold')
            if len(m.faces):replace(p,m)
    # Use each actual glass pane's plane and profile to cut matching true glazing
    # apertures; normals are measured from its thin mesh, not guessed by name.
    glass=[p for p in a['parts'] if p['group']=='front' and 'bridge_' in p['name'] and p['material']=='glass']
    for p in glass:
        m=mesh(p);center=m.vertices.mean(0);_,_,vh=np.linalg.svd(m.vertices-center,full_matrices=False);n=vh[-1]
        flat=(m.vertices-center)-np.outer((m.vertices-center)@n,n)
        cut=tm.convex.convex_hull(np.vstack([center+flat*.97+n*.60,center+flat*.97-n*.60]));cutters.append(cut)
        for frame in a['parts']:
            if not frame['name'].endswith(('bridge_square_window_frame','bridge_door_window_gasket')):continue
            if np.linalg.norm(mesh(frame).centroid-center)<.15:replace(frame,tm.boolean.difference([mesh(frame),cut],engine='manifold'))
        if 'bridge_door_window' in p['name']:
            for leaf in a['parts']:
                if leaf['name'].endswith('bridge_door_leaf') and np.linalg.norm(mesh(leaf).centroid[:2]-center[:2])<.2:replace(leaf,tm.boolean.difference([mesh(leaf),cut],engine='manifold'))
        p['material']='cabin_glass';modified.append(p['name'])
    shell=next(p for p in a['parts'] if p['name'].endswith('bridge_shell'));old_shell=mesh(shell)
    replace(shell,tm.boolean.difference([old_shell,tm.boolean.union(cutters,engine='manifold')],engine='manifold'))
    # The floor finishes flush with existing outside galleries. Its plate and
    # cross-beams occupy the existing gallery/support depth, not the aisle.
    floorplan=[(16.22,-3.30),(31.97,-3.30),(33.80,-2.705),(33.80,2.705),(31.97,3.30),(16.22,3.30)]
    add('continuous_floor',prism_xy(floorplan,f-.20,f),'cabin_floor',dict(type='convex',vertices_source_m=prism_xy(floorplan,f-.20,f).vertices.tolist()),'floor')
    for x in np.arange(17.5,32.9,1.65):cube('floor_crossbeam',[float(x),0,f-.30],[.13,6.60,.20],'steel',category='structure')
    # Reachable, low service stations. Worktop height is a design input; actual
    # end-effector reach and learned manipulation remain separate validations.
    for side in [-1,1]:
        y=side*2.73;x=c['workshop_x'];h=c['worktop_height_m']
        cube('workbench_top',[x,y,f+h-.025],[2.25,.95,.05],'cabin_worktop',True)
        for dx in [-.94,.94]:
            for dy in [-.33,.33]:cube('workbench_leg',[x+dx,y+dy,f+(h-.05)/2],[.07,.07,h-.05],'steel',True)
        for dx in [-.94,.94]:cube('workbench_foot',[x+dx,y,f+.025],[.20,.86,.05],'edge')
        cube('workbench_backboard',[x,side*3.235,f+.75],[2.35,.05,.65],'cabin_panel')
        for dx in [-.92,-.3,.3,.92]:
            cube('tool_mounting_slot',[x+dx,side*3.198,f+.72],[.16,.020,.035],'steel')
        cube('parts_tray',[x+.60,side*2.90,f+h+.04],[.55,.35,.08],'edge',True)
        cube('service_handoff_pad',[x-.60,side*2.37,f+h+.006],[.28,.22,.012],'orange')
        for xx,yy in c['cabinet_centers_x_y']:
            if yy*side<0:continue
            cube('equipment_rack',[xx,yy,f+1.28],[1.15,.88,2.56],'steel',True)
            for z in [.27,.70,1.13,1.56,1.99,2.36]:
                cube('rack_module',[xx,yy-side*.452,f+z],[1.04,.035,.34],'cabin_panel')
                for dx in [-.44,.44]:bolt('rack_fastener',[xx+dx,yy-side*.476,f+z],(0,1,0))
                for dx in [-.36,.36]:cube('rack_pull',[xx+dx,yy-side*.493,f+z],[.028,.04,.11],'edge')
                for dx in np.linspace(-.25,.25,6):cube('rack_vent',[xx+float(dx),yy-side*.472,f+z-.095],[.035,.011,.08],'black')
    # Two separated low control stations retain the central approach. Screens
    # are blank surfaces until bound to actual simulation telemetry in Godot.
    screens=[]
    for x,y in c['control_centers_x_y']:
        cube('control_base',[x,y,f+.205],[.75,1.45,.41],'cabin_panel',True)
        cube('control_top',[x-.06,y,f+.435],[.87,1.58,.05],'edge',True)
        cube('console_display_case',[x+.24,y,f+.655],[.08,1.33,.40],'steel',True)
        pane=cube('console_display_surface',[x+.192,y,f+.655],[.014,1.20,.28],'cabin_screen')
        screens.append(dict(part=pane['name'],center_source_m=[x+.18,y,f+.655],normal_source=[-1,0,0],purpose='actual driving telemetry',width=1.20,height=.28))
        for dy,mat in [(-.47,'orange'),(-.20,'ivory'),(.07,'ivory'),(.34,'yellow')]:
            m=tm.creation.cylinder(.035,.025,sections=16);m.apply_translation([x-.21,y+dy,f+.474]);add('control_button',m,mat)
        for yy in [y-.65,y+.65]:cube('console_bumper',[x-.49,yy,f+.27],[.045,.12,.40],'black')
    # Cable trays, screw-fastened ceiling panels, service luminaires and aisle
    # edge markings explain the usable interior without fake technical readouts.
    for side in [-1,1]:
        for x in [18.3,20.5,22.7,24.9,27.1,29.3,31.3]:
            cube('ceiling_panel',[x,side*1.62,14.665],[2.08,2.95,.055],'cabin_panel',category='ceiling')
            for dx in [-.91,.91]:bolt('ceiling_fastener',[x+dx,side*1.62,14.63],(0,0,1))
        cube('ceiling_cable_tray',[24.65,side*2.85,14.53],[14.8,.26,.15],'edge',category='ceiling')
        for x in [19.8,24.5,29.2]:
            cube('light_housing',[x,side*1.6,14.56],[1.90,.16,.12],'edge',category='ceiling')
            cube('light_diffuser',[x,side*1.6,14.492],[1.74,.12,.012],'cabin_light',category='ceiling')
        for x in np.arange(17.6,32.1,1.0):cube('aisle_boundary',[float(x),side*.82,f+.0015],[.72,.025,.003],'yellow',category='mark')
    # A true framed doorway needs a low seal, not the original 40 mm under-leaf
    # gap. This remains a closed door, no assertion of an actuated threshold.
    for d in doors:
        cube('door_bottom_seal',[d['center_x'],d['side']*3.58,f+.030],[1.25,.07,.06],'black',category='door')
        cube('flush_threshold',[d['center_x'],d['side']*3.42,f-.04],[1.20,.36,.08],'cabin_floor',True,category='floor')
    (OUT/'source/assembly.json.gz').write_bytes(gzip.compress(json.dumps(a,separators=(',',':')).encode(),mtime=0))
    exported=export(a,OUT/'assets/leviathan003_interior.glb')
    manifest=dict(floor_z=f,ceiling_z=c['ceiling_z'],inner_plan_xy=floorplan,central_aisle_xy_bounds=[[17.35,-.8],[32.0,.8]],doors=doors,contacts=contacts,screens=screens,added=added,modified=sorted(set(modified)),parts=len(a['parts']),**exported,
        scope='Editable cabin shell, actual openings, floor and low robot stations. Closed transport doors; actuator/boarding, manipulation, contact-transfer and complete-game performance not yet demonstrated.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,Path(__file__),ROOT/'design/vehicle.json']})
    manifest['shell_old_volume_m3']=old_shell.volume;manifest['shell_new_volume_m3']=mesh(shell).volume
    manifest['unchanged_original_parts']=sum(p==q for p,q in zip(old['parts'],a['parts']))
    (OUT/'source/interior.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:manifest[k] for k in ['parts','render_meshes','triangles','shell_old_volume_m3','shell_new_volume_m3','unchanged_original_parts']},indent=2))
if __name__=='__main__':main()
