"""Finite-joint steering requests; never sets a body pose or velocity."""
import math
import numpy as np

def wrap(x):return math.atan2(math.sin(x),math.cos(x))

class Steering:
    def __init__(self,config,bogie_positions):
        self.c=config;self.positions=np.array(bogie_positions,dtype=float)
        self.hitch_yaw=0.;self.bogie_yaw=np.zeros(len(bogie_positions));self.state={}
    def update(self,speed_request,speed,curvature_request,x,y,heading,dt):
        c=self.c;half=c['module_center_spacing_m']/2
        geometry_limit=math.tan(math.radians(min(c['operating_hitch_yaw_deg'],c['mechanical_hitch_yaw_deg'])/2))/half
        path_limit=math.tan(math.radians(c['path_hitch_equivalent_limit_deg']/2))/half
        request=float(np.clip(curvature_request,-path_limit,path_limit))
        speed_cap=math.sqrt(c['lateral_accel_command_limit_m_s2']/max(abs(request),1e-12))
        bounded_speed=float(np.clip(speed_request,-speed_cap,speed_cap))
        curvature_cap=min(geometry_limit,c['lateral_accel_command_limit_m_s2']/max(speed*speed,1.))
        if abs(request)<1e-10:tangent=0.;cross_track=y
        else:
            tangent=math.atan2(request*x,1-request*y)
            radius=1/request;cross_track=(abs(radius)-math.hypot(x,y-radius))*math.copysign(1,request)
        direction=-1. if speed_request<0 or speed<-.1 else 1.
        desired=tangent-direction*math.atan2(c['path_cross_track_gain_per_s']*cross_track,max(abs(speed),1.))
        yaw_rate=request*speed+c['path_heading_gain_per_s']*wrap(desired-heading)
        rate_cap=min(c['lateral_accel_command_limit_m_s2']/max(abs(speed),1.),geometry_limit*max(abs(speed),.1))
        yaw_rate=float(np.clip(yaw_rate,-rate_cap,rate_cap))
        correction_curvature=yaw_rate/speed if abs(speed)>.5 else request
        bounded_curvature=float(np.clip(correction_curvature,-curvature_cap,curvature_cap))
        yaw_target=-2*math.atan(half*bounded_curvature)
        rate=math.radians(c['hitch_target_rate_deg_s'])*dt
        self.hitch_yaw+=float(np.clip(yaw_target-self.hitch_yaw,-rate,rate))
        actual_request=-math.tan(self.hitch_yaw/2)/half
        target=np.arctan2(actual_request*self.positions[:,0],1-actual_request*self.positions[:,1])
        target=np.clip(target,-math.radians(c['bogie_yaw_limit_deg']),math.radians(c['bogie_yaw_limit_deg']))
        rate=math.radians(c['bogie_target_rate_deg_s'])*dt
        self.bogie_yaw+=np.clip(target-self.bogie_yaw,-rate,rate)
        self.state=dict(requested_curvature_m_inv=curvature_request,limited_curvature_m_inv=bounded_curvature,
            effective_curvature_m_inv=actual_request,speed_request_m_s=bounded_speed,yaw_rate_request_rad_s=yaw_rate,
            cross_track_error_m=cross_track,hitch_yaw_target_rad=self.hitch_yaw,bogie_yaw_targets_rad=self.bogie_yaw.tolist())
        return self.state
