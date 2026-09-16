"""Read the exported binary buffers independently; verify texture/motion contracts."""
from pathlib import Path
import json,struct,numpy as np
O=Path(__file__).resolve().parents[1];raw=(O/'assets/Sainiverse_v0.1.glb').read_bytes();n=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+n]);data=memoryview(raw)[28+n:]
def accessor(i):
 a=g['accessors'][i];v=g['bufferViews'][a['bufferView']];dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];dim={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];return np.ndarray((a['count'],dim),dtype=dtype,buffer=data,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dtype).itemsize*dim),np.dtype(dtype).itemsize))
rows=[];total=0.;covered=0.
for mesh in g['meshes']:
 for prim in mesh['primitives']:
  attr=prim['attributes'];v=accessor(attr['POSITION']);indices=accessor(prim['indices']).reshape(-1,3);uv=accessor(attr['TEXCOORD_1']);uv0=accessor(attr['TEXCOORD_0']);tri=v[indices];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5
  mapped=np.all(uv[indices,0]>=0,axis=1);valid=np.all(np.isfinite(uv));assert valid and len(uv)==len(v)
  active=uv[mapped[indices[:,0]]] if False else uv[uv[:,0]>=0]
  assert not len(active) or (np.min(active[:,0])>=0 and np.max(active[:,0])<16)
  total+=float(area.sum());covered+=float(area[mapped].sum())
  dynamic='_bogie_' in mesh['name']
  if dynamic:assert set(np.round(uv0[:,1],4)).issubset({1.,0.,-1.,-2.}),mesh['name']
  rows.append({'mesh':mesh['name'],'triangles':len(indices),'area_m2':float(area.sum()),'textured_area_m2':float(area[mapped].sum()),'uv2_finite':bool(valid),'dynamic_uv0_valid':dynamic})
r={'actual_glb_area_m2':total,'actual_textured_area_m2':covered,'actual_coverage':covered/total,'meshes':rows,'scope':'Independent binary TEXCOORD_1/triangle area read, not assignment count. Dynamic UV0 metadata is retained.'}
(O/'reports/glb_texture_audit.json').write_text(json.dumps(r,indent=2));assert covered/total>.8;print({'coverage':covered/total,'meshes':len(rows),'triangles':sum(x['triangles'] for x in rows)})
