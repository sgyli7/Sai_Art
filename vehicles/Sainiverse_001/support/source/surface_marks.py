"""Portable surface paint geometry, kept in the same static material batches.

Font outlines are authored once; no font rasterizer or decals run in the game.
All positions use source +X forward, +Y port, +Z up.
"""
from pathlib import Path
from functools import lru_cache
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from mesh_profiles import extrude_xz

FONT=Path(__file__).parent/'fonts/DejaVuSans-Bold.ttf'

class OutlinePen(BasePen):
    def __init__(self,glyphs):
        super().__init__(glyphs);self.paths=[];self.current=[]
    def _moveTo(self,p):self.current=[np.array(p,dtype=float)]
    def _lineTo(self,p):self.current.append(np.array(p,dtype=float))
    def _curveToOne(self,p1,p2,p3):
        p0=np.array(self._getCurrentPoint());p1,p2,p3=map(np.asarray,(p1,p2,p3))
        for t in np.linspace(0,1,7)[1:]:
            self.current.append((1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3)
    def _closePath(self):
        if len(self.current)>2:self.paths.append(np.array(self.current))
        self.current=[]
    def _endPath(self):self._closePath()

@lru_cache(maxsize=32)
def text_contours(text):
    font=TTFont(FONT);glyphs=font.getGlyphSet();cmap=font.getBestCmap();paths=[];advance=0
    for ch in text:
        name=cmap[ord(ch)];pen=OutlinePen(glyphs);glyphs[name].draw(pen)
        paths.extend(path+[advance,0] for path in pen.paths)
        advance+=font['hmtx'][name][0]
    font.close()
    points=np.vstack(paths);lo=points.min(axis=0);hi=points.max(axis=0)
    return tuple((path-(lo+hi)/2)/(hi[1]-lo[1]) for path in paths)

def side_paint(contours,center,side,thickness=.004):
    """Contours are viewed from outside: horizontal text reads on both sides."""
    m=extrude_xz(contours[0],0,thickness,contours[1:])
    transform=np.eye(4);transform[0,0]=-side;transform[:3,3]=center
    m.apply_transform(transform)
    m.metadata['surface_paint']=True
    m.metadata['paint_center']=list(center)
    m.metadata['paint_side']=side
    return m

def lettering(text,center,side,height):
    return side_paint([p*height for p in text_contours(text)],center,side)

def ring_paths(outer,inner,segments=48):
    a=np.arange(segments)*2*np.pi/segments
    return [np.column_stack((r*np.cos(a),r*np.sin(a))) for r in (outer,inner)]

def snow_emblem(radius=.50):
    # Visible blue snow/compass-like emblem. The unreadable caption is omitted.
    paths=[]
    for i in range(8):
        angle=i*np.pi/4;length=radius if i%2==0 else radius*.82
        rot=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        for outline in [np.array([[.02,-.026],[length,-.026],[length,.026],[.02,.026]]),
                        np.array([[length*.48,0],[length*.72,.15],[length*.80,.12],[length*.61,-.01]]),
                        np.array([[length*.48,0],[length*.72,-.15],[length*.80,-.12],[length*.61,.01]])]:
            paths.append(outline@rot.T)
    # Union avoids XOR gaps where the arms cross.
    import manifold3d
    section=manifold3d.CrossSection()
    for path in paths:section=section+manifold3d.CrossSection([path])
    return section.to_polygons()
