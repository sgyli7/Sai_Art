"""Diagnostic: only contact-cache reuse changes; always restore project bytes."""
from pathlib import Path
import subprocess,json,hashlib
from suspension_physics import ROOT
OUT=ROOT/'candidates/r023_interior/reports'
PROJECT=Path('/home/ethan/Projects/Robot_Godot_Sim2Sim/main/results/leviathan003/runtime/project.godot')
def main():
    saved=PROJECT.read_bytes();key='jolt_physics_3d/simulation/body_pair_contact_cache_enabled=false'
    assert 'body_pair_contact_cache_enabled=' not in saved.decode()
    try:
        PROJECT.write_text(saved.decode().replace('[physics]','[physics]\n\n'+key))
        with (OUT/'contact_no_cache.log').open('w') as log:
            subprocess.run(['/home/ethan/.local/bin/godot','--headless','--path',str(PROJECT.parent),'--script',str(ROOT/'godot/interior_contact_bench.gd'),'--',str(OUT/'contact_component_input.json'),str(OUT/'contact_no_cache.json')],check=True,timeout=30,stdout=log,stderr=subprocess.STDOUT)
    finally:PROJECT.write_bytes(saved)
    a=json.loads((OUT/'contact_no_cache.json').read_text());report=dict(max_speed_m_s=max(s['velocity_m_s'] for s in a['samples']),max_height_error_m=max(abs(s['height_error_m']) for s in a['samples']),runtime_restored=PROJECT.read_bytes()==saved,runtime_original_sha256=hashlib.sha256(saved).hexdigest(),setting=key)
    (OUT/'contact_cache_probe.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
