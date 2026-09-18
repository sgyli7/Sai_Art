"""SI counterpart of runtime/lift_servo.gd. Gravity is applied by the caller."""
import numpy as np
def efforts(q,v,target,masses,payload,dt):
 k,d=80000.,14000.;q=np.asarray(q);v=np.asarray(v);target=np.asarray(target)
 m3=float(masses[3])+payload;m2=float(masses[2])+m3;m1=float(masses[1])+m2
 mass=np.array([[m1,m2,m3],[m2,m2,m3],[m3,m3,m3]])
 force=mass@np.linalg.solve(mass+np.eye(3)*(dt*d+dt*dt*k),k*(target[1:]-q[1:])-(d+dt*k)*v[1:])
 horizontal=(k*(target[0]-q[0])-(d+dt*k)*v[0])/(1+(d*dt+k*dt*dt)/(masses[0]+m1))
 return np.r_[horizontal,force]
