"""Resolve the 18 September inspection against shared source-space clearances."""
import numpy as np
import trimesh as tm
from mechanical_revision import mesh,replace,boxmesh,cyl

def author(a,add,box,rod,O):
    removed=[];moved=[];contacts=a['habitable_revision']['contacts']
    def shift(p,d):
        m=mesh(p);m.apply_translation(d);replace(p,m)
        for c in contacts:
            if c['name']==p['name']:c['vertices_source_m']=(np.array(c['vertices_source_m'])+d).tolist()
        moved.append(p['name'])
    for p in list(a['parts']):
        n=p['name'];m=mesh(p);c=m.bounds.mean(0);side=np.sign(c[1])
        if any(t in n for t in ['roof_machine_', 'continuous_cooling_elbow','cooling_case_coupling','cooling_roof_collar']):
            shift(p,np.array([0,side*3.1,0]))
        elif '_fore_vent_' in n:
            # Four grilles, not only the inner pair: fit the complete set between
            # the 2.52 m stairhouse and the +/-8 m equipment-house sides.
            target=side*(3.0 if abs(c[1])<4. else 6.2)
            v=np.array(p['vertices']);v[:,1]=(v[:,1]-c[1])*(2.70/3.64)+target;p['vertices']=v.tolist();moved.append(n)
        elif any(t in n for t in ['engineer_seat','engineer_arm','seat_floor_anchor']):
            shift(p,np.array([0,-side*.28,0]))
        elif n.endswith('_bridge_lower_trim') or n.endswith('_bridge_vertical_seam'):
            removed.append(p)
        elif n.endswith('_ceiling_service_run'):
            # Aft bulkhead slopes forward toward the roof: conduit starts inside.
            v=np.array(p['vertices']);v[v[:,0]<17.12,0]=17.12;p['vertices']=v.tolist()
        elif n.endswith('_fore_roof_end_post') and c[0]>13 and abs(c[1])<.1:removed.append(p)
        elif n.endswith('_fore_roof_end_rail') and c[0]>13:
            removed.append(p)
            for s in [-1,1]:box('landing_guard_return',[c[0],s*4.585,c[2]],[.045,6.33,.045],'edge','front')
        elif n.endswith('_engineer_switch_surface') and side<0:p['cockpit_transform']['rotate_uv_180']=True
        elif n.endswith('_center_navigation'):p['cockpit_transform']['rotate_uv_90']=True
        elif n.endswith('_lift_controls'):
            # Deck-mounted call station, not a free-floating button enclosure.
            box('lift_call_station_foot',[c[0],c[1],7.48],[.32,.30,.06],'steel',p['group'])
            rod('lift_call_station_post',[c[0],c[1],7.51],[c[0],c[1],7.94],.046,'steel',p['group'])
        elif n.endswith('_bridge_roof_rung_stand'):removed.append(p)
    for p in removed:a['parts'].remove(p)
    # Continuous ladder stiles, only three actual wall brackets per side.
    for s in [-1,1]:
        for x in [20.85,21.35]:
            rod('ladder_stile',[x,s*3.74,11.51],[x,s*3.74,15.23],.027,'edge','front')
            for z in [11.68,13.22,14.76]:
                rod('ladder_bracket',[x,s*3.49,z],[x,s*3.74,z],.027,'edge','front')
                box('ladder_wall_pad',[x,s*3.513,z],[.11,.026,.14],'steel','front')
    a['acceptance_revision']={'removed':[p['name'] for p in removed],'relocated':moved,
        'engineer_seat_console_gap_m':.285,'notes':'Roof HVAC and front grilles clear the occupied stair volume. Source contacts move with seats.'}
