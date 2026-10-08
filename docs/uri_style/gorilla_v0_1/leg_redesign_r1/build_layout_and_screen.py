"""Proposed sagittal layout and conditional statics; not an assembled CAD model."""
from pathlib import Path
import ctypes as C
import ctypes.util
import json
import math

ROOT = Path(__file__).resolve().parent
STATIONS = {'HIP': (-.02, 1.43), 'J1': (.26, .94), 'J2': (-.13, .49), 'ANKLE': (.06, .16)}
ACTUATORS = {
    'J2': {'pivot': STATIONS['J2'], 'fixed_local': (.48, .33), 'moving_local': (.1425, -.2475)},
    'ankle_pitch': {'pivot': STATIONS['ANKLE'], 'fixed_local': (-.04, .30), 'moving_local': (.24, -.01)},
}

def render(svg_path, png_path, width, height):
    a = C.CDLL(ctypes.util.find_library('rsvg-2'))
    c = C.CDLL(ctypes.util.find_library('cairo'))
    g = C.CDLL(ctypes.util.find_library('gobject-2.0'))
    class Rect(C.Structure):
        _fields_ = [('x', C.c_double), ('y', C.c_double), ('width', C.c_double), ('height', C.c_double)]
    a.rsvg_handle_new_from_data.argtypes = [C.c_void_p, C.c_size_t, C.POINTER(C.c_void_p)]
    a.rsvg_handle_new_from_data.restype = C.c_void_p
    a.rsvg_handle_render_document.argtypes = [C.c_void_p, C.c_void_p, C.POINTER(Rect), C.POINTER(C.c_void_p)]
    a.rsvg_handle_render_document.restype = C.c_int
    c.cairo_image_surface_create.argtypes = [C.c_int, C.c_int, C.c_int]
    c.cairo_image_surface_create.restype = C.c_void_p
    c.cairo_create.argtypes = [C.c_void_p]
    c.cairo_create.restype = C.c_void_p
    c.cairo_surface_write_to_png.argtypes = [C.c_void_p, C.c_char_p]
    c.cairo_surface_write_to_png.restype = C.c_int
    c.cairo_destroy.argtypes = [C.c_void_p]
    c.cairo_surface_destroy.argtypes = [C.c_void_p]
    g.g_object_unref.argtypes = [C.c_void_p]
    raw = svg_path.read_bytes(); buf = C.create_string_buffer(raw); err = C.c_void_p()
    h = a.rsvg_handle_new_from_data(buf, len(raw), C.byref(err))
    assert h
    surface = c.cairo_image_surface_create(0, width, height); context = c.cairo_create(surface)
    assert a.rsvg_handle_render_document(h, context, C.byref(Rect(0, 0, width, height)), C.byref(err))
    assert c.cairo_surface_write_to_png(surface, str(png_path).encode()) == 0
    c.cairo_destroy(context); c.cairo_surface_destroy(surface); g.g_object_unref(h)

def main():
    pairs = [('HIP', 'J1'), ('J1', 'J2'), ('J2', 'ANKLE')]
    lengths = [math.dist(STATIONS[a], STATIONS[b]) for a, b in pairs]
    # This is a deliberately separate force envelope, not a validated whole-robot mass.
    self_mass_allowance = 2200.; external_vertical_mass_equivalent = 3000.; gravity = 9.81
    static_total = (self_mass_allowance + external_vertical_mass_equivalent) * gravity
    amplified_single = static_total * 1.5
    load = {'provisional_self_mass_kg': self_mass_allowance, 'external_downward_force_mass_equivalent_kg': external_vertical_mass_equivalent,
            'scope': 'Conservative force sensitivity, NOT measured mass or 3-ton payload qualification. All force on one foot is an envelope, not demonstrated single-foot whole-body equilibrium.',
            'static_total_N': static_total, 'static_symmetric_each_foot_N': static_total / 2, 'amplified_single_foot_N': amplified_single,
            'force_multiplier_assumption': 1.5, 'CoP_forward_z_m': [-.19, .31]}
    samples = {}
    for name, d in ACTUATORS.items():
        A, B = d['fixed_local'], d['moving_local']; rows = []
        for step in range(801):
            deg = -20 + step * .05; t = math.radians(deg)
            b = (B[0]*math.cos(t)-B[1]*math.sin(t), B[0]*math.sin(t)+B[1]*math.cos(t))
            length = math.dist(A, b); lever = (b[0]*A[1]-b[1]*A[0]) / length
            rows.append((deg, length, lever))
        arm = min(abs(r[2]) for r in rows)
        moment = amplified_single * max(abs(x-d['pivot'][0]) for x in load['CoP_forward_z_m'])
        # Idealized paired hydraulic family, no chosen SKU or installed envelope certification.
        bore, rod, pressure, back = .08, .04, 30e6, .3e6
        cap = math.pi*bore*bore/4; ann = math.pi*(bore*bore-rod*rod)/4
        pair_pull = 2*(pressure*ann-back*cap)
        samples[name] = {'angle_samples': len(rows), 'relative_angle_range_deg': [-20,20],
                         'minimum_absolute_effective_arm_m': arm, 'signed_arm_range_m': [min(r[2] for r in rows), max(r[2] for r in rows)],
                         'eye_length_range_m': [min(r[1] for r in rows),max(r[1] for r in rows)],
                         'required_geometric_stroke_m': max(r[1] for r in rows)-min(r[1] for r in rows),
                         'worst_vertical_force_moment_Nm': moment, 'required_combined_cylinder_force_N': moment/arm,
                         'conditional_family': {'count':2,'bore_m':bore,'rod_m':rod,'pressure_Pa':pressure,'return_pressure_Pa':back,
                                                'ideal_pair_pull_force_N':pair_pull,'ideal_min_torque_Nm':pair_pull*arm,
                                                'minimum_ideal_capacity_to_demand_ratio':pair_pull*arm/moment},
                         'scope':'Neutral-pose specified-CoP force moment paired conservatively with individual-joint lever-sweep minimum. Not a combined-pose worst case. Ideal planar pressure only; no friction, efficiency, actual cylinder dimensions, operating temperature, joints, shell or collision qualification.'}
    fore, heel, cop, hinge, stop_arm = .32, -.18, .31, .18, .10
    fore_reaction = amplified_single * (cop-heel)/(fore-heel)
    stop_force = fore_reaction*(fore-hinge)/stop_arm
    foot = {'fixed_heel':True,'unloaded_forefoot_hinge_only':True,'separate_ground_pads':True,
            'fore_reaction_point_z_m':fore,'heel_reaction_point_z_m':heel,'sensitivity_CoP_z_m':cop,
            'fore_reaction_N':fore_reaction,'heel_reaction_N':amplified_single-fore_reaction,
            'proposed_fore_hinge_z_m':hinge,'proposed_stop_effective_arm_m':stop_arm,
            'combined_compression_stop_force_N':stop_force,'two_stop_nominal_area_each_m2':.06*.04,
            'nominal_mean_stop_pressure_Pa':stop_force/(2*.06*.04),
            'scope':'Two prescribed contact resultants and nominal stop-face average only; actual pressure distribution, unilateral face geometry, local bending, bearing/lock/fastener strength and sole deflection unverified.'}
    spec = {'revision':'LEG_R1','status':'new_art_and_sagittal_architecture_candidate_not_physical_acceptance',
            'coordinates':'Art coordinates: X width, Y height, Z forward depth. Engineering thread uses a different axis convention; all conversions must be explicit.',
            'stations_Z_Y_m':STATIONS,'serial_links':['HIP-J1','J1-J2','J2-ANKLE'],'link_lengths_m':lengths,
            'ankle_to_ground_y_m':.16,'original_overall_height_m':2.65,'original_overall_width_m':2.586977,
            'overall_depth':'Re-evaluate after 3D integration; do not assume old 1.071836m depth remains exact.',
            'actuator_eye_proposals':ACTUATORS,'load_sensitivity':load,'actuator_screens':samples,'foot_sensitivity':foot,
            'pending':['Finite connected CAD and actual complete drive assemblies','Both-side bearing and shaft bending/torsion sizing','Carrier mounting, pin/stop/lock strength and fatigue','Continuous kinematic collision and hose routing','Foot contact and whole-body equilibrium','Net material mass/inertia and integrated energy/heat'],
            'physical_accepted':False}
    (ROOT/'layout_and_load_screen.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
    xy = lambda p:(650-600*p[0],1050-600*p[1])
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200"><rect width="1200" height="1200" fill="white"/>',
         '<g font-family="DejaVu Sans" fill="#274363"><text x="35" y="50" font-size="25">LEG R1 / PROPOSED SAGITTAL LAYOUT</text><text x="35" y="86" font-size="18">THREE SERIAL LINKS / FRONT TO LEFT / NOT CAD</text></g>',
         '<path d="M140 1050H980" stroke="#8298af" stroke-width="2"/>']
    for i,(a,b) in enumerate(pairs):
        x,y=xy(STATIONS[a]);u,v=xy(STATIONS[b]);w=[100,90,80][i]
        s += [f'<path d="M{x} {y}L{u} {v}" stroke="#243746" stroke-width="{w+8}" stroke-linecap="round"/>',
              f'<path d="M{x} {y}L{u} {v}" stroke="#168dd0" stroke-width="{w}" stroke-linecap="round"/>',
              f'<text x="{(x+u)/2-150}" y="{(y+v)/2}" font-size="20" font-family="sans-serif" fill="#274363">L{i+1}: {lengths[i]:.3f} m</text>']
    s += ['<path d="M610 975L685 1012L800 1012L800 1045H640L575 1015L510 1015L405 1045H365V1020L490 985Z" fill="#ebe6d8" stroke="#243746" stroke-width="6"/>',
          '<path d="M365 1045H550V1055H365Z M650 1045H810V1055H650Z" fill="#343a3d"/>']
    for name,p in STATIONS.items():
        x,y=xy(p);s.append(f'<circle cx="{x}" cy="{y}" r="34" fill="#354450" stroke="#eab13b" stroke-width="5"/><text x="{x+65}" y="{y+7}" font-size="22" font-family="sans-serif" fill="#274363">{name}</text>')
    s += ['<text x="35" y="1130" font-size="18" font-family="sans-serif" fill="#274363">Hip -> forward knee -> rear hock -> forward ankle</text>',
          '<text x="35" y="1160" font-size="18" font-family="sans-serif" fill="#274363">Ankle compact; broad stopped forefoot; fixed separate heel</text>','</svg>']
    svg=ROOT/'references/proposed_three_link_layout.svg';svg.write_text('\n'.join(s));render(svg,svg.with_suffix('.png'),1200,1200)
    print(json.dumps({'lengths_m':lengths,'screen':samples,'foot':foot},indent=2))

if __name__ == '__main__':
    main()
