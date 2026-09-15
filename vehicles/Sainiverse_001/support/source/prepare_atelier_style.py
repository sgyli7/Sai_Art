"""Reuse the user's actual sim2sim art direction without changing geometry/physics."""
from pathlib import Path
import hashlib
import gzip
import json
import shutil
from suspension_physics import ROOT

GAME = Path('/home/ethan/Projects/Robot_Godot_Sim2Sim/main')
OUT = ROOT / 'candidates/r024_atelier'


def main():
    for folder in ['assets', 'physics', 'reports', 'reference_sources']:
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    paths = ['godot/atelier/enamel.gdshader', 'godot/atelier/ink.gdshader', 'godot/atelier/workshop.gd',
             'godot/hub/sai_materials.gd', 'godot/science_station/station.gd', 'godot/science_station/sky.gdshader',
             'docs/science-station/media/command.jpg', 'docs/science-station/media/service.jpg']
    manifest = {}
    for name in paths:
        p = GAME / name
        target = OUT / 'reference_sources' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        manifest[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    enamel = (GAME / paths[0]).read_text()
    ink = (GAME / paths[1]).read_text()
    (OUT / 'assets/enamel.gdshader').write_text(enamel)
    (OUT / 'assets/ink.gdshader').write_text(ink)
    shutil.copyfile(GAME / 'godot/science_station/sky.gdshader', OUT / 'assets/sky.gdshader')
    base = (ROOT / 'candidates/r022_runtime/assets/tensioned_tracks_texture.gdshader').read_text()
    vertex_start = base.index('void vertex(){')
    fragment_start = base.index('void fragment(){')
    deformation = base[vertex_start:fragment_start]
    declarations = base[:vertex_start].replace('render_mode cull_back;', 'render_mode cull_back, specular_disabled;')
    enamel_declarations = enamel[enamel.index('uniform float shade_softness'):enamel.index('void vertex()')]
    record_surface = 'surface_position=VERTEX;surface_normal=NORMAL;world_normal=MODEL_NORMAL_MATRIX*NORMAL;'
    v = deformation.rstrip()[:-1] + record_surface + '\n}\n'
    shading = enamel[enamel.index('void fragment()'):].replace('pigment.rgb', 'paint.rgb')
    (OUT / 'assets/track_enamel.gdshader').write_text(declarations + enamel_declarations + v + shading)
    ink_declarations = ink[ink.index('uniform vec4'):ink.index('void vertex()')]
    ink_vertex = ink[ink.index('void vertex() {') + len('void vertex() {'):ink.index('void fragment()')].strip()[:-1]
    iv = deformation.rstrip()[:-1] + ink_vertex + '\n}\n'
    (OUT / 'assets/track_ink.gdshader').write_text(declarations.replace('cull_back, specular_disabled', 'cull_front, unshaded, shadows_disabled') + ink_declarations + iv + 'void fragment(){ALBEDO=ink_color.rgb;}\n')
    palette = json.loads(gzip.decompress((ROOT / 'candidates/r023_interior/source/assembly.json.gz').read_bytes()))['colors']
    config = dict(palette=palette, hatch_strength=.045, line_pixels=.65, ink_color='24232b', ink_fade_start_m=100., ink_fade_end_m=360.,
                  ambient_color='c6c3d6', ambient_energy=.48, sun_color='fff9ed', sun_energy=.96,
                  ground_color='4d5d60', cabin_light_energy=1.5,
                  basis='Exact sim2sim enamel light bands/hatching and ink shader; unchanged r023 original pigments and linear tone mapping. Ink fade scaled for full carrier. No fog or palette substitution. Physics and geometry unchanged.')
    (OUT / 'style.json').write_text(json.dumps(config, indent=2) + '\n')
    previous = ROOT / 'candidates/r023_interior'
    for name in ['suspended.xml', 'native_spec.json', 'parameters.json', 'interior_contacts.json']:
        shutil.copyfile(previous / 'physics' / name, OUT / 'physics' / name)
    bindings = json.loads((previous / 'bindings.json').read_text())
    bindings['style'] = str(OUT / 'style.json')
    bindings['scope'] = 'Full r023 carrier geometry and independent physics, sim2sim atelier/station style. Static robot scale figures only; no new robot task or full-game integration claim.'
    (OUT / 'bindings.json').write_text(json.dumps(bindings, indent=2) + '\n')
    (OUT / 'reference_sources/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(OUT)


if __name__ == '__main__':
    main()
