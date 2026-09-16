"""Authored folding boarding ramp: one hinged plate per existing robot lift."""
import numpy as np
import trimesh as tm

def author(a,lifts,add,box,rod):
 a['colors']['ramp_steel']='61676B'
 for lift in lifts:
  cx,y,z=lift['pivot'];side=lift['side'];name=lift['name']+'_ramp';pivot=[cx,y+side*1.1,z+.125]
  a['groups'][name]=pivot
  box('boarding_ramp_plate',[cx,pivot[1],pivot[2]+1.0],[2.0,.04,2.0],'ramp_steel',name,'boarding_ramp')
  for dx in [-.97,.97]:box('boarding_ramp_edge',[cx+dx,pivot[1]-side*.025,pivot[2]+1.0],[.045,.012,2.0],'yellow',name,'boarding_ramp')
  rod('boarding_ramp_hinge',[cx-1.12,pivot[1],pivot[2]],[cx+1.12,pivot[1],pivot[2]],.055,'steel',lift['groups'][3])
  lift['ramp']={'name':name,'pivot':pivot,'axis':[-side,0,0],'mass_kg':120.,'size_m':[2.,.04,2.],'com_source_m':[0,0,1.],'range_rad':[0.,1.76],'torque_cap_Nm':3000.}
