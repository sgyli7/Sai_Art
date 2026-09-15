"""Per-part artwork selection. No geometry is added or changed."""
import numpy as np
import zlib

def apply(a):
 selected=[]
 rules={
  
  'crane_pedestal':(0,[0]),
  'roof_machine_case':(2,[1]),'panel_base':(3,[0]),
  'panel_base_top_hatch':(0,[2]),'bridge_roof_hatch':(0,[2]),
  'fore_roof_access':(0,[2]),'aft_end_panel':(1,[0]),
 }
 for p in a['parts']:
  name=p['name'].split('_',1)[-1]
  if name=='middle_service_shell':
   a['colors']['art_workbay_wall']=a['colors'][p['material']];p['material']='art_workbay_wall'
   selected.append(dict(name=p['name'],group=p['group'],role='art_workbay_wall',mapping='three aligned service covers on starboard wall only'));continue
  if name not in rules:continue
  v=np.array(p['vertices']);lo=v.min(0);hi=v.max(0);tile,axes=rules[name]
  base=p['material'];mat='art_'+base;a['colors'][mat]=a['colors'][base];p['material']=mat
  p['art_uv']=dict(tile=tile,axes=axes,bounds=[lo.tolist(),hi.tolist()])
  selected.append(dict(name=p['name'],group=p['group'],role=mat,tile=tile,axes=axes))
 # Painted wear is explicitly assigned to functional surfaces, never sprinkled geometry.
 wear_rules={'fore_service_shell':[0,1],'bridge_shell':[0,1],'bridge_roof':[2],
 'fore_service_door_leaf':[1],'bridge_lower_hatch_leaf':[1],'bridge_door_leaf':[1],
 'crane_boom':[0],'crane_root_cheek':[0],'crane_pedestal_hatch':[1],
 'sealed_reservoir_shell':[0,1,2],'rooftop_receiver':[0,1,2]}
 for p in a['parts']:
  label=p['name'].split('_',1)[-1];seed=zlib.crc32(p['name'].encode());kind=None;tile=([0,8,12][seed%3])+((seed//3)%4);axes=None
  if p['name'].endswith('_Sainiverse_wordmark'):kind='logo';tile=4+seed%4;axes=[1]
  elif p['name'].endswith('_lift_edge_warning'):kind='warn';axes=[2]
  elif label=='crane_tip_cheek':kind='warn';axes=[0]
  elif label in wear_rules:kind='wear';axes=wear_rules[label]
  elif label.startswith('container_') and any(k in label for k in ['_side_-1','_side_1','_closed_front_panel','_door_leaf_','_roof'] ) and not '_roof_rib_' in label:kind='wear';axes=[0,1,2]
  if kind is None:continue
  base=p['material'];mat=kind+'_'+base;a['colors'][mat]=a['colors'][base];p['material']=base if kind=='wear' else mat
  v=np.array(p['vertices']);p['art_uv']=dict(tile=tile,axes=axes,bounds=[v.min(0).tolist(),v.max(0).tolist()],flip_u=bool(seed%2),usage=kind,grid=4)
  selected.append(dict(name=p['name'],group=p['group'],role=mat,tile=tile,axes=axes,wear_variant=seed%3))
 return selected
