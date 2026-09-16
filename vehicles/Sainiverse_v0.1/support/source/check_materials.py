"""Check glTF linear factors and actual Godot-imported sRGB material values."""
from pathlib import Path
import gzip,json,struct,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
with gzip.open(ROOT/'source/assembly.json.gz','rt') as f:palette=json.load(f)['colors']
binary=(ROOT/'assets/leviathan003.glb').read_bytes()
length,kind=struct.unpack_from('<II',binary,12);assert kind==0x4e4f534a
gltf=json.loads(binary[20:20+length])
native=next(json.loads(line) for line in (ROOT/'reports/materials-after.log').read_text().splitlines() if line.startswith('{'))
assert native['glb_sha256']==hashlib.sha256(binary).hexdigest()
errors={}
for m in gltf['materials']:
    name=m['name'];srgb=np.array(list(bytes.fromhex(palette[name])))/255.
    linear=np.where(srgb<=.04045,srgb/12.92,((srgb+.055)/1.055)**2.4)
    factor=np.array(m['pbrMetallicRoughness']['baseColorFactor'])[:3]
    exported=float(np.max(abs(factor-linear)))
    imported=float(np.max(abs(np.array(native['colors'][name])[:3]-srgb)))
    assert exported<1e-12 and imported<1e-6,name
    errors[name]={'glb_linear_error':exported,'godot_srgb_error':imported}
report={'passed':True,'glb_sha256':native['glb_sha256'],'materials':errors,'scope':'Base material parameter parity; lights, tonemapping, reflections and display are not calibrated between engines.'}
(ROOT/'reports/material_validation.json').write_text(json.dumps(report,indent=2));print('PASS: all',len(errors),'materials match the source palette through native Godot import')
