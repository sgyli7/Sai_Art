"""Occupied-side lining and curated company markings, not random detail scatter."""
import copy,json
import numpy as np
import trimesh as tm
from company_stickers import build as stickers

def author(a,add,O):
    marks=stickers();placements=[]
    a['colors']['company_decal']='FFFFFF'
    a['material_properties']['company_decal']={'double_sided':False,'roughness':.86}
    # Split EXISTING inward triangles: the exterior pigment and the actual shell
    # apertures remain intact. No duplicate coplanar inner skin, no new polygons.
    shell=next(p for p in a['parts'] if p['name'].endswith('_bridge_shell'))
    m=tm.Trimesh(shell['vertices'],shell['faces'],process=False);c=m.triangles_center;n=m.face_normals
    inward=((n[:,1]*c[:,1]<-.1)&(abs(c[:,1])<3.32)&(abs(n[:,1])>.25)) | ((n[:,0]<-.3)&(c[:,0]>32)&(c[:,0]<33.81)) | ((n[:,0]>.3)&(c[:,0]<17.1))
    inward &= (c[:,2]>11.35)&(c[:,2]<14.66)
    q=copy.deepcopy(shell);q['name']='r032_cockpit_occupied_wall_skin';q['faces']=m.faces[inward].tolist();q['material']='cabin_lining';q['interior_category']='wall';q.pop('art_uv',None);a['parts'].append(q)
    shell['faces']=m.faces[~inward].tolist()
    # The lounge shell already has its own floor / ceiling faces, slightly above
    # the collision-floor datum. Finish those visible faces instead of burying
    # a new texture plane beneath them.
    rest=next(p for p in a['parts'] if p['name'].endswith('_fore_service_shell'))
    rm=tm.Trimesh(rest['vertices'],rest['faces'],process=False);rc=rm.triangles_center;rn=rm.face_normals;keep=np.ones(len(rm.faces),bool)
    for cat,mask,material in [('floor',(rc[:,2]<8)&(rn[:,2]>.9),'cabin_floor'),('ceiling',(rc[:,2]>12)&(rn[:,2]<-.9),'cabin_lining')]:
        q=copy.deepcopy(rest);q['name']='r032_lounge_occupied_'+cat;q['faces']=rm.faces[mask].tolist();q['material']=material;q['interior_category']=cat;q.pop('art_uv',None);a['parts'].append(q);keep &= ~mask
    rest['faces']=rm.faces[keep].tolist()
    a['colors']['cabin_floor']='596167'
    # Warm neutral lining belongs to occupied surfaces, regardless of body livery.
    # Connector/coaming weather skins retain the exterior `ivory` role; their
    # separately authored inset lining parts already use `cabin_lining`.
    for p in a['parts']:
        if any(t in p['name'] for t in ['lounge_inner_lining','lounge_end_lining']):p['material']='cabin_lining'
        if p.get('interior_category') in ['wall','ceiling','workbench','console']:
            p['interior_finish']=True

    def place(art,c,u,up,width,group='front',zone='interior'):
        item=marks[art];height=width/item['aspect'];c=np.asarray(c,float);u=np.asarray(u,float);up=np.asarray(up,float)
        verts=[c+u*x*width/2+up*y*height/2 for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        mesh=tm.Trimesh(verts,[[0,1,2],[0,2,3]],process=False)
        name=add('company_'+art,mesh,'company_decal',group)
        p=a['parts'][-1];x0,y0,x1,y1=item['uv_rect']
        p['native_uv']=[[x0,1-y1],[x1,1-y1],[x1,1-y0],[x0,1-y0]]
        p['company_sticker']=art
        if zone=='interior':p['interior_category']='marking'
        placements.append(dict(name=name,art=art,body=group,zone=zone,center_source_m=c.tolist(),width_m=width,height_m=height,normal=np.cross(u,up).tolist()))
    for s in [-1,1]:
        place('compact_light',[-5.55,s*10.51,10.60],[-s,0,0],[0,0,1],1.00,zone='exterior')
        # Inward normal -Y on port wall, +Y on starboard; both read from aisle.
        place('horizontal_dark',[20.85,s*3.285,13.33],[s,0,0],[0,0,1],.94)
        place('field_strip',[27.80,s*1.947,11.78],[s,0,0],[0,0,1],1.22)
        place('compact_light',[30.093,s*1.58,12.43],[0,-1,0],[0,0,1],.26)
        place('worn_medium' if s<0 else 'field_hex',[7.4,s*7.747,9.65],[s,0,0],[0,0,1],1.10)
        place('field_id',[12.323,s*4.30,9.34],[0,-1,0],[0,0,1],.26)
        place('worn_banner',[14.8,s*1.087,12.84],[s,0,0],[0,0,1],.88)
        place('horizontal_dark' if s<0 else 'field_id',[16.759,s*2.1,12.50],[0,1,0],[0,0,1],1.05 if s<0 else .27)
        # Existing exterior bridge wordmark region is replaced, never overprinted.
        place('horizontal_light',[31.45,s*3.556,11.72],[-s,0,0],[0,0,1],1.25,zone='exterior')
    a['parts']=[p for p in a['parts'] if 'Sainiverse_wordmark' not in p['name']]
    for hull,art in [('front','worn_stripe'),('rear','field_strip'),('tail','worn_banner')]:
        cx=a['groups'][hull][0]
        for s in [-1,1]:place(art,[cx+7.2,s*13.137,6.08],[-s,0,0],[0,0,1],2.05,hull,'exterior')
    for i,p in enumerate([p for p in a['parts'] if p['name'].endswith('_crane_pedestal_hatch')]):
        v=np.asarray(p['vertices']);lo=v.min(0);hi=v.max(0);c=(hi+lo)/2;s=np.sign(c[1]);c[1]+=s*(hi[1]-lo[1])/2+s*.007
        c[2]+=.15
        place('field_id' if i%2==0 else 'worn_vertical',c,[-s,0,0],[0,0,1],.36,p['group'],'exterior')
        p['company_replaces_service_logo']=True
    # Marks follow each authored cargo body and its physical face dimensions.
    for item in a['equipment_actuation']['cargo_catalog']:
        c=np.array(item['center']);size=np.array(item['size']);variant=(item['bay']*2+item['row']+item['tier'])%6
        group='cargo_rear_b0_r2_t2' if item['name']=='container_b0_r2_t2' else 'rear'
        for s in [-1,1]:
            p=c.copy();p[0]+=s*(size[0]/2+.009);p[2]+=.15
            place('fleet_'+str(variant),p,[0,s,0],[0,0,1],min(1.55,size[1]*.7),group,'cargo')
        if item['row'] in [0,5]:
            s=-1 if item['row']==0 else 1;p=c.copy();p[1]+=s*(size[1]/2+.009)
            place('field_strip' if variant%2 else 'worn_banner',p,[-s,0,0],[0,0,1],1.75,group,'cargo')
    (O/'assets/company/placements.json').write_text(json.dumps(placements,indent=2))
    a['company_identity']={'placements':len(placements),'new_triangles':len(placements)*2,'source':'assets/company/manifest.json'}
