"""Finite door velocity servo, parked opening gate and drive interlock."""
import numpy as np


class CabinAccess:
    def __init__(self, config):
        self.c = config
        self.names = [d['name'] for d in config['doors']]
        n = len(self.names)
        self.requests = np.zeros(n, dtype=bool)
        self.targets = np.zeros(n)
        self.torques = np.zeros(n)
        self.latch_torques = np.zeros(n)
        self.latched = np.ones(n, dtype=bool)
        self.stall = np.zeros(n)
        self.obstructed = np.zeros(n, dtype=bool)
        self.q = np.zeros(n)
        self.dq = np.zeros(n)
        self.power = 0.
        self.drive_permitted = False

    def step(self, q, dq, vehicle_speed, dt):
        self.q = np.asarray(q).copy()
        self.dq = np.asarray(dq).copy()
        maximum = np.radians(self.c['maximum_open_deg'])
        for i in range(len(self.names)):
            if self.requests[i] and abs(vehicle_speed) <= self.c['opening_vehicle_speed_limit_m_s']:
                self.latched[i] = False
                self.targets[i] = maximum
                self.obstructed[i] = False
            elif not self.requests[i] and not self.obstructed[i]:
                self.targets[i] = 0.
            closing = self.targets[i] < q[i] - .001
            rate = np.clip(self.c['position_gain_s_inv'] * (self.targets[i] - q[i]), -self.c['maximum_angular_speed_rad_s'], self.c['maximum_angular_speed_rad_s'])
            limit = self.c['close_torque_limit_Nm'] if closing else self.c['open_torque_limit_Nm']
            limit = min(limit, self.c['motor_power_limit_W'] / max(abs(dq[i]), .001))
            torque = float(np.clip(self.c['velocity_gain_Nms_rad'] * (rate - dq[i]), -limit, limit))
            stopped = closing and q[i] > .07 and abs(dq[i]) < .005 and abs(torque) > .95 * self.c['close_torque_limit_Nm']
            self.stall[i] = self.stall[i] + dt if stopped else 0.
            if self.stall[i] >= .4:
                self.obstructed[i] = True
                self.targets[i] = q[i]
                torque = 0.
            if not self.requests[i] and not self.obstructed[i] and abs(q[i]) < self.c['latch_capture_angle_rad'] and abs(dq[i]) < self.c['latch_capture_speed_rad_s']:
                self.latched[i] = True
            self.latch_torques[i] = np.clip(-self.c['latch_stiffness_Nm_rad'] * q[i] - self.c['latch_damping_Nms_rad'] * dq[i], -self.c['latch_torque_limit_Nm'], self.c['latch_torque_limit_Nm']) if self.latched[i] else 0.
            if self.latched[i]:torque = 0.
            self.torques[i] = torque
        self.power = float(np.maximum(self.torques * dq, 0).sum())
        self.drive_permitted = bool(self.latched.all() and not self.requests.any() and not self.obstructed.any() and np.max(np.abs(q)) < .015 and np.max(np.abs(dq)) < .02)
        return self.torques

    def state(self):
        return dict(angles_rad=self.q.tolist(), angular_rates_rad_s=self.dq.tolist(), targets_rad=self.targets.tolist(),
                    torques_Nm=self.torques.tolist(), obstructed=self.obstructed.tolist(), power_W=self.power,
                    drive_permitted=self.drive_permitted, latched=self.latched.tolist(), latch_torques_Nm=self.latch_torques.tolist())
