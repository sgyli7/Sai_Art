"""Targeted structure corrections, before/after solid intersections, authored detail.
No changes to carrier contact proxies or its main load/kinematic model.
"""
import json, math
import numpy as np
import trimesh as tm
from shapely.geometry import MultiPoint

def mesh(p):return tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
def replace(p,m):p.update(vertices=m.vertices.tolist(),faces=m.faces.tolist())
def rounded_box(bounds,r):
    lo,hi=np.array(bounds);pts=[]
    for sx in [-1,1]:
      for sy in [-1,1]:
       for sz in [-1,1]:
        center=(lo+hi)/2+np.array([sx,sy,sz])*((hi-lo)/2-r)
        for phi in np.linspace(0,math.pi/2,4):
         for theta in np.linspace(0,math.pi/2,4):
          pts.append(center+r*np.array([sx*math.cos(phi)*math.cos(theta),sy*math.cos(phi)*math.sin(theta),sz*math.sin(phi)]))
    return tm.convex.convex_hull(pts)
def refine(a,box,rod,add,role,out):
    changes=[];intersections=[];parts=a['parts']
    # Preserve container corner posts/locking details; roof pressings become texture.
    ribs=[p for p in parts if 'container_' in p['name'] and '_roof_rib_' in p['name']]
    a['parts']=parts=[p for p in parts if p not in ribs]
    changes.append({'change':'container roof pressing detail moved to filtered normal/albedo atlas','removed_parts':len(ribs),'removed_triangles':sum(len(p['faces']) for p in ribs)})
    # Infill sits behind the bay's bracing and frame, rather than swallowing it.
    for p in parts:
      if p['name'].endswith('aft_module_infill'):
        v=np.array(p['vertices']);v[:,1]-=np.sign(v[:,1].mean())*.15;p['vertices']=v.tolist()
    # Bearings need visible clearance in the deep side fascia. Before/after
    # booleans check the actual collar solid, not only its bounding box.
    collars=[p for p in parts if p['name'].endswith('steering_collar')]
    for p in parts:
      n=p['name']
      if not any(s in n for s in ['side_fascia','lower_web','lower_chord']):continue
      m=mesh(p)
      for c in collars:
        if c['group']!=p['group']:continue
        cm=mesh(c)
        if not np.all(np.minimum(m.bounds[1],cm.bounds[1])-np.maximum(m.bounds[0],cm.bounds[0])>0):continue
        before=abs(tm.boolean.intersection([m,cm],engine='manifold').volume)
        if before<1e-7:continue
        # Circular bearing recess, 80 mm radial clearance, only local fascia.
        radius=max(np.ptp(cm.vertices[:,0]),np.ptp(cm.vertices[:,1]))/2+.08
        cut=tm.creation.cylinder(radius=radius,height=np.ptp(cm.vertices[:,2])+.16,sections=32);cut.apply_translation(cm.bounds.mean(0))
        m=tm.boolean.difference([m,cut],engine='manifold')
        after=abs(tm.boolean.intersection([m,cm],engine='manifold').volume)
        intersections.append({'part':n,'collar':c['name'],'before_m3':before,'after_m3':after})
      replace(p,m)
    # End guards were 0.13 m above deck and 0.65 m short of side guards.
    for p in parts:
      if p['name'].split('_',1)[-1].startswith('front_end_rail'):
        v=np.array(p['vertices']);v[:,2]-=.10
        if p['name'].endswith('_post'):v[v[:,2]<7.6,2]=7.45
        p['vertices']=v.tolist()
    for x in [-16.65,16.65]:
      for side in [-1,1]:
        for z in [8.08,8.63]:rod('end_guard_join',[math.copysign(16,x),side*12.9,z],[x,side*12.9,z],.0225,'edge','front')
    # Keep the service houses squared; only the cantilevered cabin roof is formed.
    for p in parts:
      if p['name'].endswith('bridge_roof'):
        old=mesh(p);poly=MultiPoint(old.vertices[:,:2]).convex_hull.buffer(-.32).buffer(.32,resolution=4)
        m=tm.creation.extrude_polygon(poly,height=np.ptp(old.vertices[:,2]),engine='earcut');m.apply_translation([0,0,old.bounds[0,2]])
        replace(p,m);changes.append({'change':'rounded cabin roof plan','radius_m':.32})
    # Receiver bottle and saddle share one mounting datum above the workbay roof.
    bottle=next(p for p in parts if p['name'].endswith('rooftop_receiver'))
    for p in parts:
      if p['name'].endswith(('rooftop_receiver','receiver_strap')):
        v=np.array(p['vertices']);v[:,2]+=.30;p['vertices']=v.tolist()
      if p['name'].endswith('receiver_seat'):
        m=mesh(p);v=m.vertices.copy();lo,hi=m.bounds
        v[:,2]=14.10+(v[:,2]-lo[2])/(hi[2]-lo[2])*.53;m.vertices=v
        cut=tm.creation.cylinder(radius=.685,height=5,sections=32);cut.apply_transform(tm.geometry.align_vectors([0,0,1],[1,0,0]));cut.apply_translation([-1,float(v[:,1].mean()),14.90])
        replace(p,tm.boolean.difference([m,cut],engine='manifold'))
    changes.append({'change':'receiver clear of roof on concave saddles','tank_bottom_m':14.23,'roof_top_m':14.10})
    # Middle service house lands on a continuous recessed foundation plinth.
    box('workbay_foundation',(-1.70,0,7.775),(11.40,21.0,.65),role('303438'),'front')
    box('forehouse_sill',(9,0,7.475),(10,16,.05),role('303438'),'front')
    # Compact receiver bottle: domed ends, same 4 m overall envelope and mount axis.
    for p in parts:
      if p['name'].endswith('rooftop_receiver'):
        rings=[];faces=[];r=.67;receiver_y=float(np.array(p['vertices'])[:,1].mean())
        for x,radius in [(-3,0.01),(-2.95,.26),(-2.82,.48),(-2.60,.62),(-2.33,r),(.33,r),(.60,.62),(.82,.48),(.95,.26),(1,.01)]:
          rings.extend([[x,receiver_y+radius*math.cos(t),14.90+radius*math.sin(t)] for t in np.linspace(0,2*math.pi,24,endpoint=False)])
        for j in range(9):
          for k in range(24):
            n=(k+1)%24;faces.extend([[j*24+k,(j+1)*24+k,(j+1)*24+n],[j*24+k,(j+1)*24+n,j*24+n]])
        rings.extend([[-3,receiver_y,14.90],[1,receiver_y,14.90]])
        for k in range(24):
          n=(k+1)%24;faces.extend([[240,k,n],[241,216+n,216+k]])
        m=tm.Trimesh(vertices=rings,faces=faces,process=True);m.fix_normals();assert m.is_watertight and m.volume>0;replace(p,m)
      if 'instrument_ribbon_panel' in p['name']:p['material']=role('485054')
    # The upper ring is equipment enclosure, not occupied window glazing.
    # Interior walkway barriers obstruct service doors; keep the outside edge guard.
    a['parts']=parts=[p for p in parts if not p['name'].endswith(('_fore_house_seam','_fore_house_deck_rail','_fore_house_deck_post'))]
    # Antenna roots are real flanged sockets, not rods pushed into the roof.
    for p in list(parts):
      n=p['name']
      if n.endswith('_antenna'):
        v=np.array(p['vertices']);center=v.mean(0);z=v[:,2].min();x,y=center[:2]
        rod('antenna_socket',[x,y,z-.08],[x,y,z+.24],.15,'steel','front')
        box('antenna_footplate',(x,y,z-.06),(.50,.50,.08),'steel','front')
        for dx in [-.18,.18]:
          for dy in [-.18,.18]:rod('antenna_mount_bolt',[x+dx,y+dy,z-.02],[x+dx,y+dy,z+.025],.032,'silver','front')
    # Roof cooling pipes terminate in bolted collars; their former ends floated.
    for side in [-1,1]:
      rod('cooling_case_coupling',[8.60,side*1.40,14.20],[8.80,side*1.40,14.20],.25,'steel','front')
      rod('cooling_roof_collar',[7.80,side*1.40,13.30],[7.80,side*1.40,13.48],.26,'steel','front')
    # Slim continuous identity ribbon, kept clear of doors and service vents.
    red=role('BE162B')
    for side in [-1,1]:
      box('mechanical_house_identity_ribbon',(9,side*8.012,12.69),(8.30,.024,.14),red,'front')
      box('status_lens_mount',(13.05,side*8.05,11.80),(.34,.12,1.00),role('242A2C'),'front')
      for z,mat,color in [(12.10,'status_power','62AF96'),(11.80,'status_motion','75B7D1'),(11.50,'status_lift','E6A82D')]:
        a['colors'][mat]=color
        rod('status_bezel',[13.05,side*8.10,z],[13.05,side*8.17,z],.103,'steel','front')
        rod('status_lens',[13.05,side*8.165,z],[13.05,side*8.195,z],.074,mat,'front')
    assert all(x['after_m3']<1e-6 for x in intersections)
    (out/'reports/structure_refinement.json').write_text(json.dumps({'changes':changes,'collar_intersections':intersections,'scope':'Visual assembly clearance checks. Local bearing relief is not a certified load-bearing redesign.'},indent=2))
