"""Bind unchanged authored axle hardware to the finite hydraulic candidate."""
from pathlib import Path
import hashlib,json
from suspension_physics import ROOT
OUT=ROOT/'candidates/r020_hydraulics'
def main():
    previous=ROOT/'candidates/r019_running_gear/bindings.json'
    binding=json.loads(previous.read_text())
    binding['scope']='Finite hydraulic lower-wheel forces, unchanged r019 authored guided-axle exterior. 72 wheel/axle carrier bindings and 21 physical exterior groups. Original fixed belt loop; no physical tensioner. Reservoir, accumulator and circuit hardware are not yet authored; current body mass ledger is provisional. No interior, boarding or operating cranes.'
    files=[previous,Path(__file__),Path(binding['glb']),Path(binding['shader']),Path(binding['native_blend']),OUT/'physics/native_spec.json']
    binding['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (OUT/'bindings.json').write_text(json.dumps(binding,indent=2)+'\n')
    print('r020 binds the unchanged complete r019 native model and export')
if __name__=='__main__':main()
