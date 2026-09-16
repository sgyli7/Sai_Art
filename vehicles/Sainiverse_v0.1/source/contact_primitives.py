"""Lossless replacement of box-shaped convex contacts with box primitives.

Only merge adjoining rectangles with identical extents on the other two axes.
No collision is removed or approximated; window/door/stair voids remain voids.
"""
import numpy as np

def compact(shapes):
    others=[];boxes=[];converted=0
    for q in shapes:
        q=dict(q)
        if q['type']=='box':
            c=np.asarray(q['center_source_m']);h=np.asarray(q['size_m'])/2;lo,hi=c-h,c+h
        else:
            v=np.asarray(q['vertices_source_m']);lo=v.min(0);hi=v.max(0)
            if len(np.unique(np.round(v,5),axis=0))!=8 or not np.all(np.minimum(abs(v-lo),abs(v-hi))<2e-6):others.append(q);continue
            q.pop('vertices_source_m');q['type']='box';converted+=1
        boxes.append([q,lo,hi])
    before=len(boxes);again=True
    while again:
        again=False
        for i,(a,lo,hi) in enumerate(boxes):
            for j in range(i+1,len(boxes)):
                b,low,high=boxes[j]
                if a.get('body','front')!=b.get('body','front'):continue
                for axis in range(3):
                    ij=[k for k in range(3) if k!=axis]
                    if np.max(abs(lo[ij]-low[ij]))>2e-6 or np.max(abs(hi[ij]-high[ij]))>2e-6:continue
                    if abs(hi[axis]-low[axis])>2e-6 and abs(high[axis]-lo[axis])>2e-6:continue
                    a['merged_from']=a.get('merged_from',[a['name']])+b.get('merged_from',[b['name']])
                    boxes[i]=[a,np.minimum(lo,low),np.maximum(hi,high)];boxes.pop(j);again=True;break
                if again:break
            if again:break
    for q,lo,hi in boxes:q.update(center_source_m=((lo+hi)/2).tolist(),size_m=(hi-lo).tolist());others.append(q)
    return others,dict(input_shapes=len(shapes),box_conversions=converted,adjacent_box_merges=before-len(boxes),output_shapes=len(others),scope='Exact axis-aligned primitive equivalence and adjacent-box union only; no convex approximation or deletion of apertures.')
