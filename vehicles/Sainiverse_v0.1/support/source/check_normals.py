"""Read actual GLB buffers; every primitive must carry finite unit normals."""
from pathlib import Path
import struct,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
b=(ROOT/'assets/leviathan003.glb').read_bytes();size,tag=struct.unpack_from('<II',b,12)
g=json.loads(b[20:20+size]);binary_start=20+size+8
rows=[]
for mesh in g['meshes']:
    for p in mesh['primitives']:
        assert 'NORMAL' in p['attributes'],mesh['name']
        a=g['accessors'][p['attributes']['NORMAL']];v=g['bufferViews'][a['bufferView']]
        assert a['componentType']==5126 and a['type']=='VEC3'
        offset=binary_start+v.get('byteOffset',0)+a.get('byteOffset',0)
        n=np.ndarray((a['count'],3),dtype='<f4',buffer=b,offset=offset,strides=(v.get('byteStride',12),4))
        assert np.isfinite(n).all()
        error=float(np.max(abs(np.linalg.norm(n,axis=1)-1)))
        assert error<1e-5,(mesh['name'],error)
        rows.append(dict(mesh=mesh['name'],vertices=a['count'],unit_error=error))
report=dict(passed=True,meshes=len(rows),vertices=sum(x['vertices'] for x in rows),max_unit_error=max(x['unit_error'] for x in rows),details=rows)
(ROOT/'reports/normals_validation.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='details'})
