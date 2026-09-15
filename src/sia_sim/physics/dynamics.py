"""Deterministic 4-DOF rigid-body vessel dynamics model."""

from __future__ import annotations

import math

import numpy as np

from sia_sim.contracts.data import EnvironmentState, VesselState
from sia_sim.contracts.scenario import VesselConfig
from sia_sim.physics.environment import KNOTS_TO_M_S
from sia_sim.physics.forces import (
    apparent_wind,
    hydrodynamic_damping,
    righting_moment,
    rudder_forces,
    sail_forces,
)
from sia_sim.physics.integrator import rk4_step


class VesselDynamics:
    """Rigid body planar dynamics with roll (Surge, Sway, Yaw, Roll).

    State array indices:
      0: x (m)
      1: y (m)
      2: psi (heading in rad)
      3: u (surge velocity in m/s)
      4: v (sway velocity in m/s)
      5: r (yaw rate in rad/s)
      6: phi (heel angle in rad)
      7: p (roll rate in rad/s)
    """

    def __init__(self, config: VesselConfig) -> None:
        self.config = config
        self.mass = config.displacement_kg
        self.loa = config.loa_m
        self.beam = config.beam_m

        # Added mass approximations for displacement yacht
        self.m_u = self.mass * 1.08
        self.m_v = self.mass * 1.85
        # Mass moments of inertia (kg*m^2)
        self.i_z = (1.0 / 12.0) * self.mass * (self.loa**2 + self.beam**2) * 1.5
        self.i_x = (1.0 / 12.0) * self.mass * (self.beam**2 + 2.5**2) * 1.3

        # State vector
        init_u = config.initial_sog_kt * KNOTS_TO_M_S
        init_psi = math.radians(config.initial_heading_deg)
        init_phi = math.radians(config.initial_heel_deg)

        self._state = np.array(
            [0.0, 0.0, init_psi, init_u, 0.0, 0.0, init_phi, 0.0],
            dtype=np.float64,
        )
        self._rudder_angle_deg = 0.0

    @classmethod
    def from_config(cls, config: VesselConfig) -> VesselDynamics:
        return cls(config)

    def reset(self, config: VesselConfig | None = None) -> None:
        """Reset dynamics state to initial configuration."""
        if config is not None:
            self.config = config
            self.mass = config.displacement_kg
            self.loa = config.loa_m
            self.beam = config.beam_m

        init_u = self.config.initial_sog_kt * KNOTS_TO_M_S
        init_psi = math.radians(self.config.initial_heading_deg)
        init_phi = math.radians(self.config.initial_heel_deg)

        self._state = np.array(
            [0.0, 0.0, init_psi, init_u, 0.0, 0.0, init_phi, 0.0],
            dtype=np.float64,
        )
        self._rudder_angle_deg = 0.0

    def step(
        self,
        dt_s: float,
        env: EnvironmentState,
        rudder_deg: float = 0.0,
        mainsheet_pct: float = 100.0,
        wave_impact_force_n: float = 0.0,
        wave_impact_roll_moment_nm: float = 0.0,
    ) -> VesselState:
        """Advance dynamics state by dt_s and return immutable VesselState."""
        self._rudder_angle_deg = rudder_deg

        def derivatives(state: np.ndarray, _t: float) -> np.ndarray:
            _x, _y, psi, u, v, r, phi, p = state

            heading_deg = math.degrees(psi) % 360.0
            heel_deg = math.degrees(phi)

            # 1. Apparent wind
            aws_m_s, awa_deg = apparent_wind(
                u_m_s=u,
                v_m_s=v,
                heading_deg=heading_deg,
                tws_m_s=env.true_wind_speed_m_s,
                twa_deg=env.true_wind_angle_deg,
            )

            # 2. Sail forces
            x_sail, y_sail, k_sail, n_sail = sail_forces(
                aws_m_s=aws_m_s,
                awa_deg=awa_deg,
                mainsheet_pct=mainsheet_pct,
            )

            # 3. Rudder forces
            y_rudder, n_rudder = rudder_forces(
                u_m_s=u,
                v_m_s=v,
                r_rad_s=r,
                rudder_angle_deg=rudder_deg,
                heel_deg=heel_deg,
            )

            # 4. Hydrodynamic damping
            x_drag, y_drag, k_roll_drag, n_yaw_drag = hydrodynamic_damping(
                u_m_s=u,
                v_m_s=v,
                r_rad_s=r,
                p_rad_s=p,
                loa_m=self.loa,
                beam_m=self.beam,
                mass_kg=self.mass,
            )

            # 5. Righting moment
            k_righting = righting_moment(heel_deg=heel_deg, mass_kg=self.mass)

            # Total forces and moments
            total_x = x_sail + x_drag
            total_y = y_sail + y_rudder + y_drag + wave_impact_force_n
            total_k = k_sail + k_roll_drag + k_righting + wave_impact_roll_moment_nm
            total_n = n_sail + n_rudder + n_yaw_drag

            # Kinematics
            dx = u * math.cos(psi) - v * math.sin(psi)
            dy = u * math.sin(psi) + v * math.cos(psi)
            dpsi = r

            # Rigid body accelerations
            du = (total_x + self.m_v * v * r) / self.m_u
            dv = (total_y - self.m_u * u * r) / self.m_v
            dr = total_n / self.i_z
            dphi = p
            dp = total_k / self.i_x

            return np.array([dx, dy, dpsi, du, dv, dr, dphi, dp], dtype=np.float64)

        # Integrate step
        self._state = rk4_step(self._state, derivatives, dt_s)

        # Normalize angles
        self._state[2] = self._state[2] % (2.0 * math.pi)  # heading
        # Clamp heel to [-pi, pi]
        if self._state[6] > math.pi:
            self._state[6] -= 2.0 * math.pi
        elif self._state[6] < -math.pi:
            self._state[6] += 2.0 * math.pi

        x, y, psi, u, v, r, phi, p = self._state

        heading_deg = math.degrees(psi) % 360.0
        sog_m_s = math.hypot(u, v)

        # Course over ground = heading + drift angle
        drift_deg = math.degrees(math.atan2(v, max(0.01, u))) if sog_m_s > 0.05 else 0.0
        cog_deg = (heading_deg + drift_deg) % 360.0

        return VesselState(
            x_m=float(x),
            y_m=float(y),
            heading_deg=float(heading_deg),
            sog_m_s=float(sog_m_s),
            cog_deg=float(cog_deg),
            heel_deg=float(math.degrees(phi)),
            pitch_deg=0.0,  # Planar dynamics approximation
            roll_rate_deg_s=float(math.degrees(p)),
            yaw_rate_deg_s=float(math.degrees(r)),
            rudder_angle_deg=float(self._rudder_angle_deg),
        )
