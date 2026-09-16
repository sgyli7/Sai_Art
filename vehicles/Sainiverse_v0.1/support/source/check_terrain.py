"""Verify the actual native terrain against its captured original collision data.
Run after the sequential minimal and full-scene startup regression loops.
"""
from pathlib import Path
import hashlib,json,os,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'reports'
GAME=Path('/home/ethan/Projects/Robot_Godot_Sim2Sim/main')
RUNTIME=GAME/'results/leviathan003/runtime'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
adapter=ROOT/'godot/terrain.gd'
expected=re.search(r'^## Source terrain SHA256: ([0-9a-f]{64})$',adapter.read_text(),re.M).group(1)
assert sha(RUNTIME/'polar_range/terrain.gd')==expected
out=R/'terrain_data_fixed_r013.json'
script=ROOT/'source/diagnostics/terrain_data.gd'
command=['/home/ethan/.local/bin/godot','--path',str(RUNTIME),'--rendering-method','forward_plus','--disable-vsync','--script',str(script),'--',str(adapter),str(out)]
with (R/'terrain-data-fixed-r013.log').open('w') as log:
    subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'DISPLAY':':1'},timeout=90,check=True)
original=json.loads((R/'terrain_data_original_r013.json').read_text())
fixed=json.loads(out.read_text())
minimal=json.loads((R/'terrain_fixed_r013/result.json').read_text())
minimal_source=json.loads((R/'terrain_fixed_r013/source.json').read_text())
full=json.loads((R/'startup_r013_fixed/result.json').read_text())
checks={
 'native_collision_data_valid':original['passed'] and fixed['passed'],
 'all_collision_vertices_bit_identical':original['faces_sha256']==fixed['faces_sha256'],
 '647520_triangles':original['triangles']==fixed['triangles']==647520,
 'minimal_128_fresh_processes':minimal['passed'] and len(minimal['attempts'])>=128,
 'minimal_current_adapter':minimal_source['dependencies_sha256']['godot/terrain.gd']==sha(adapter),
 'original_terrain_unchanged':minimal_source['terrain_sha256']==expected,
 'full_scene_64_fresh_processes':full['passed'] and len(full['attempts'])>=64,
}
checks['full_scene_current_control_sources']=all(
 json.loads((R/'startup_r013_fixed'/f"{row['attempt']:03d}"/'source.json').read_text())['sha256'][name]==sha(ROOT/name)
 for row in full['attempts'] for name in ['godot/terrain.gd','godot/drive_scene.gd','godot/runtime.gd','assets/physics.json','training/policy.json'])
report={'passed':all(checks.values()),'checks':checks,'adapter_sha256':sha(adapter),'source_terrain_sha256':expected,'test_sha256':sha(script),'faces_sha256':fixed['faces_sha256'],'minimal_attempts':len(minimal['attempts']),'full_scene_attempts':len(full['attempts']),'scope':'Application avoids the reproduced Mesh.get_faces readback crash; engine internals and other hardware not diagnosed. R013 full-scene stress inherited only for unchanged terrain/control code; current visual asset requires its separate rendered run. Startup stress is not FPS or driving validation.'}
(R/'terrain_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 1)
