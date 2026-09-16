"""1-D perspective fit to manually inspected, collinear wheel-hub landmarks.

Dimensionless model: upper-wheel center span=1. Fit a projective map separately
for each photograph. No original focal length, camera pose or metric scale is
inferred. Uniform +/-2 px perturbations quantify annotation sensitivity only.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.optimize import least_squares
ROOT=Path(__file__).resolve().parents[1]
ATT=ROOT/'references'
LANDMARKS={4:[186,245,348,429,577,693,917,1097],5:[291,504,760,907,1097,1202,1346,1426]}
def projection(x,p):return (p[0]*x+p[1])/(p[2]*x+1)
def fit(u,centers=None,seed=None):
    def coordinates(p):
        c=np.arange(-3,1)*p[3] if centers is None else np.asarray(centers)
        return (c[:,None]+[-.5,.5]).ravel()
    init=seed if seed is not None else [100,u[-2:].mean(),-.09 if u[0]<200 else .05]+([21/8.3] if centers is None else [])
    q=least_squares(lambda p:projection(coordinates(p),p)-u,init)
    predicted=projection(coordinates(q.x),q.x)
    return q.x,predicted,float(np.sqrt(np.mean((predicted-u)**2)))
rows=[];rng=np.random.default_rng(3011)
for number,values in LANDMARKS.items():
    u=np.array(values,dtype=float);p,pred,rms=fit(u)
    old=(np.array([-49.5,-26.5,-11.5,11.5])-11.5)/8.3
    _,prior,prior_rms=fit(u,old)
    fixed=(np.arange(-3,1)*21/8.3)
    _,rounded,rounded_rms=fit(u,fixed)
    sensitivity=[fit(u+rng.uniform(-2,2,len(u)),seed=p)[0][3] for _ in range(250)]
    rows.append(dict(reference=number,reference_sha256=hashlib.sha256((ATT/f'image-{number}.png').read_bytes()).hexdigest(),image_resolution=[1600,900],landmark_u_px=values,landmark_description='Near-side outer upper hub centers, rear-to-front, two end wheels per bogie; manually inspected',fitted_pitch_per_wheel_span=float(p[3]),fitted_pitch_at_inherited_span_m=float(p[3]*8.3),uniform_rms_px=rms,uniform_predicted_u_px=pred.tolist(),previous_rms_px=prior_rms,previous_predicted_u_px=prior.tolist(),rounded_21m_rms_px=rounded_rms,annotation_sensitivity_pitch_ratio_5_95=np.percentile(sensitivity,[5,95]).tolist(),projective_coefficients=p[:3].tolist()))
report=dict(method=__doc__,rows=rows,selected=dict(bogie_rows_x_m=[-52.5,-31.5,-10.5,10.5],pitch_m=21,upper_wheel_span_m=8.3),limits=['Manual pixels, not original CAD dimensions.','Collinear observations cannot recover full camera pose or vertical/lateral shape.','Perturbation interval is not a confidence interval for all model errors.','Near-equidistant arrangement is supported; exact equality is a chosen simplification.'])
(ROOT/'reports/layout_reference_measurement.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
