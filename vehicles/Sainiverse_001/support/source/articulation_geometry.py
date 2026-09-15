"""Authored telescopic coupling with offset yaw/pitch/roll bearing axes.

Geometry and kinematic frames are shared by the candidate assembly and tests.
No engineering load capacity is inferred from these reconstructed dimensions.
"""
from pathlib import Path
import json,math
import numpy as np
import trimesh as tm
from mesh_profiles import extrude_xz,circle_xz

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'design/articulation_candidate.json').read_text())
YAW=np.array(C['reference_anchor_m'])
PITCH=YAW+np.array(C['pitch_axis_offset_m'])
ROLL=PITCH+np.array(C['roll_axis_offset_from_pitch_m'])
GROUPS={'hitch_slide':YAW.tolist(),'hitch_yaw':YAW.tolist(),'hitch_pitch':PITCH.tolist()}

def poses(extension=0.,yaw=0.,pitch=0.,roll=0.):
    """World transforms applied to neutral source vertices; angles in radians."""
    slide=tm.transformations.translation_matrix([-extension,0,0])
    y=slide@tm.transformations.rotation_matrix(yaw,[0,0,1],point=YAW)
    p=y@tm.transformations.rotation_matrix(pitch,[0,1,0],point=PITCH)
    r=p@tm.transformations.rotation_matrix(roll,[1,0,0],point=ROLL)
    return {'front':np.eye(4),'hitch_slide':slide,'hitch_yaw':y,'hitch_pitch':p,'rear':r}

def build():
    parts=[]
    def add(name,group,mesh,material='edge'):
        assert mesh.is_volume,(name,'not an oriented closed solid')
        parts.append(dict(name=name,group=group,material=material,mesh=mesh))
        return mesh
    def box(name,g,p,size,mat='edge'):
        m=tm.creation.box(size);m.apply_translation(p);return add(name,g,m,mat)
    def cyl(name,g,p,r,length,axis=(0,0,1),mat='steel',inner=0.):
        m=tm.creation.annulus(r_min=inner,r_max=r,height=length,sections=40) if inner else tm.creation.cylinder(r,length,sections=40)
        m.apply_transform(tm.geometry.align_vectors([0,0,1],axis));m.apply_translation(p)
        return add(name,g,m,mat)
    def rod(name,g,a,b,r=.12,mat='edge'):
        a,b=np.array(a),np.array(b)
        return cyl(name,g,(a+b)/2,r,float(np.linalg.norm(b-a)),b-a,mat)
    hx,_,hz=YAW;px=PITCH[0];rx=ROLL[0]

    # Fixed sleeve, actual through bore and two structural saddle collars.
    cyl('telescopic_outer_sleeve','front',[-16.45,0,hz],.90,5.90,(1,0,0),'edge',.70)
    for i,x in enumerate((-19.18,-18.00,-14.05)):
        cyl(f'slide_bushing_{i}','front',[x,0,hz],.715,.22,(1,0,0),'black',.66)
    for i,x in enumerate((-16.,-14.)):
        cyl(f'sleeve_saddle_{i}','front',[x,0,hz],1.03,.42,(1,0,0),'steel',.89)
        for side in (-1,1):
            rod(f'sleeve_saddle_leg_{i}_{side}','front',[x,side*.83,hz+.15],[x,side*2,6.7],.22)
            if i==1:box(f'sleeve_deck_foot_{side}','front',[x,side*2,6.7],[1.,.9,.9],'steel')
            for dx in (-.30,.30):cyl(f'sleeve_mount_bolt_{i}_{side}_{dx}','front',[x+dx,side*2,7.18],.09,.10,mat='silver')
    # At full extension 1.7 m remains within the sleeve, across two bushings.
    cyl('telescopic_inner_tube','hitch_slide',[-16.8,0,hz],.65,6.20,(1,0,0),'silver',.48)
    box('yaw_stator_front_spine','hitch_slide',[hx+1.30,0,hz],[.35,1.70,2.10])
    # Separate upper and lower fork plates leave a clear central rotating boss.
    for side in (-1,1):
        z=hz+side*.90
        outline=[(hx-.65,-.80),(hx+1.50,-.80),(hx+1.50,.80),(hx-.65,.80)]
        m=extrude_xz(outline,z,.30,[circle_xz(hx,0,.32,40)])
        swap=np.eye(4);swap[:3,:3]=[[1,0,0],[0,0,1],[0,1,0]];m.apply_transform(swap)
        add(f'yaw_stator_ear_{side}','hitch_slide',m)
    cyl('yaw_rotor_boss','hitch_yaw',YAW,.53,1.40,mat='edge')
    cyl('yaw_vertical_pin','hitch_yaw',YAW,.29,2.40,mat='silver')
    for side in (-1,1):
        cyl(f'yaw_pin_cap_{side}','hitch_yaw',[hx,0,hz+side*1.15],.44,.15,mat='steel')
        # Offset fork carries the pitch axis behind the vertical yaw pin.
        rod(f'yaw_fork_arm_{side}','hitch_yaw',[hx-.28,side*.35,hz],[px+.48,side*.95,hz],.20)
        outline=circle_xz(px,hz,.43,40)
        add(f'pitch_fixed_ear_{side}','hitch_yaw',extrude_xz(outline,side*.95,.26,[circle_xz(px,hz,.25,40)]))

    cyl('pitch_rotor_boss','hitch_pitch',PITCH,.38,1.40,(0,1,0),'edge')
    cyl('pitch_transverse_pin','hitch_pitch',PITCH,.23,2.50,(0,1,0),'silver')
    for side in (-1,1):
        cyl(f'pitch_pin_cap_{side}','hitch_pitch',[px,side*1.23,hz],.33,.10,(0,1,0),'steel')
        corners=[[px-.10,0,hz+side*.32],[px-.10,0,hz+side*.80],
                 [rx,0,hz+side*.80],[rx,0,hz+side*.52]]
        for i in range(3):rod(f'roll_bearing_bridge_{side}_{i}','hitch_pitch',corners[i],corners[i+1],.10)
    cyl('roll_bearing_housing','hitch_pitch',ROLL,.58,.45,(1,0,0),'edge',.41)
    cyl('roll_sleeve_bushing','hitch_pitch',ROLL,.42,.39,(1,0,0),'black',.39)

    cyl('rear_roll_shaft','rear',[-25.01,0,hz],.38,2.38,(1,0,0),'silver',.25)
    for x in (-24.50,-23.77):cyl(f'roll_retaining_flange_{x}','rear',[x,0,hz],.55,.10,(1,0,0),'steel',.37)
    for side in (-1,1):rod(f'rear_shaft_drawbar_{side}','rear',[-26,side*2,hz],[-25.6,0,hz],.28)
    # A recognisable service plate on the fixed sleeve, not a fake sensor.
    box('sleeve_service_plate','front',[-16.7,-.905,hz],[1.20,.06,.62],'ivory')
    for x in (-17.15,-16.25):
        for z in (hz-.21,hz+.21):cyl(f'service_plate_fastener_{x}_{z}','front',[x,-.95,z],.04,.04,(0,1,0),'silver')
    return parts

def sleeve_clearance_tool():
    """Clear the moving tube tunnel through fixed deck/crossbeam geometry."""
    m=tm.creation.cylinder(.94,7.30,sections=48)
    m.apply_transform(tm.geometry.align_vectors([0,0,1],[1,0,0]));m.apply_translation([-16.65,0,YAW[2]])
    return m
