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
)
from sia_sim.physics.integrator import rk4_step
from sia_sim.physics.sails.rig import SailRig, create_standard_sloop_rig


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

    def __init__(self, config: VesselConfig, rig: SailRig | None = None) -> None:
        self.config = config
        self.mass = config.displacement_kg
        self.loa = config.loa_m
        self.beam = config.beam_m
        self.sail_area_m2 = config.sail_area_m2
        self.mast_height_m = config.mast_height_m
        self.sail_trim_pct = config.sail_trim_pct
        self.gm_m = 1.35 if self.beam >= 4.0 else 1.10

        self.rig = rig or create_standard_sloop_rig(
            mainsail_area_m2=self.sail_area_m2 * 0.5,
            headsail_area_m2=self.sail_area_m2 * 0.5,
            mast_height_m=self.mast_height_m,
            loa_m=self.loa,
        )
        if hasattr(self.config, "active_sails") and self.config.active_sails:
            self.rig.configure_active_sails(self.config.active_sails)
        elif hasattr(self.config, "sail_plan") and self.config.sail_plan:
            self.rig.set_sail_plan(self.config.sail_plan)

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
        self._time_s = 0.0

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
            self.sail_area_m2 = config.sail_area_m2
            self.mast_height_m = config.mast_height_m
            self.sail_trim_pct = config.sail_trim_pct
            self.gm_m = 1.35 if self.beam >= 4.0 else 1.10
            self.rig = create_standard_sloop_rig(
                mainsail_area_m2=self.sail_area_m2 * 0.5,
                headsail_area_m2=self.sail_area_m2 * 0.5,
                mast_height_m=self.mast_height_m,
                loa_m=self.loa,
            )
            if hasattr(self.config, "active_sails") and self.config.active_sails:
                self.rig.configure_active_sails(self.config.active_sails)
            elif hasattr(self.config, "sail_plan") and self.config.sail_plan:
                self.rig.set_sail_plan(self.config.sail_plan)
        else:
            if hasattr(self.config, "active_sails") and self.config.active_sails:
                self.rig.configure_active_sails(self.config.active_sails)
            elif hasattr(self.config, "sail_plan") and self.config.sail_plan:
                self.rig.set_sail_plan(self.config.sail_plan)

        init_u = self.config.initial_sog_kt * KNOTS_TO_M_S
        init_psi = math.radians(self.config.initial_heading_deg)
        init_phi = math.radians(self.config.initial_heel_deg)

        self._state = np.array(
            [0.0, 0.0, init_psi, init_u, 0.0, 0.0, init_phi, 0.0],
            dtype=np.float64,
        )
        self._rudder_angle_deg = 0.0
        self._time_s = 0.0

    def step(
        self,
        dt_s: float,
        env: EnvironmentState,
        rudder_deg: float = 0.0,
        mainsheet_pct: float = 100.0,
        wave_impact_force_n: float = 0.0,
        wave_impact_roll_moment_nm: float = 0.0,
        wave_impact_yaw_moment_nm: float = 0.0,
        ambient_wave_roll_moment_nm: float = 0.0,
    ) -> VesselState:
        """Advance dynamics state by dt_s and return immutable VesselState."""
        self._rudder_angle_deg = rudder_deg
        self._time_s += dt_s

        def derivatives(state: np.ndarray, _t: float = 0.0) -> np.ndarray:
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

            # 2. Sail forces from multi-sail aerodynamic rig
            rig_res = self.rig.evaluate(
                aws_m_s=aws_m_s,
                awa_deg=awa_deg,
                heel_deg=heel_deg,
                mainsheet_pct=mainsheet_pct,
            )
            x_sail = rig_res.thrust_n
            y_sail = rig_res.side_force_n
            k_sail = rig_res.heeling_moment_nm
            n_sail = rig_res.yawing_moment_nm

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
            k_righting = righting_moment(heel_deg=heel_deg, mass_kg=self.mass, gm_m=self.gm_m)

            # Total forces and moments (including continuous ambient wave excitation)
            total_x = x_sail + x_drag
            total_y = y_sail + y_rudder + y_drag + wave_impact_force_n
            total_k = (
                k_sail
                + k_roll_drag
                + k_righting
                + wave_impact_roll_moment_nm
                + ambient_wave_roll_moment_nm
            )
            total_n = n_sail + n_rudder + n_yaw_drag + wave_impact_yaw_moment_nm

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

        # Pitch kinematics derived from wave slope encounter and slamming moments
        wave_dir_rad = math.radians(env.true_wind_angle_deg)
        mu = wave_dir_rad - psi
        wavelength = max(5.0, (9.80665 * (env.wave_period_s**2)) / (2.0 * math.pi))
        wave_k = (2.0 * math.pi) / wavelength
        omega_0 = (2.0 * math.pi) / max(0.1, env.wave_period_s)
        # Encounter frequency
        omega_e = max(0.1, abs(omega_0 - wave_k * u * math.cos(mu)))
        # Longitudinal wave slope pitch amplitude with 3D sea cross-coupling
        pitch_wave_amp_rad = 0.5 * wave_k * env.wave_height_m * (0.85 * abs(math.cos(mu)) + 0.15)
        # Wave pitch angle oscillation
        phase = omega_e * self._time_s + wave_k * (x * math.cos(psi) + y * math.sin(psi))
        pitch_wave_deg = math.degrees(pitch_wave_amp_rad * math.sin(phase))

        # Wave slam impact induces bow-down pitch moment
        slam_pitch_deg = -3.5 * (wave_impact_force_n / 12000.0) if wave_impact_force_n > 0 else 0.0
        total_pitch_deg = max(-25.0, min(25.0, pitch_wave_deg + slam_pitch_deg))

        return VesselState(
            x_m=float(x),
            y_m=float(y),
            heading_deg=heading_deg,
            sog_m_s=sog_m_s,
            cog_deg=cog_deg,
            heel_deg=math.degrees(phi),
            pitch_deg=round(total_pitch_deg, 2),
            roll_rate_deg_s=math.degrees(p),
            yaw_rate_deg_s=math.degrees(r),
            rudder_angle_deg=self._rudder_angle_deg,
        )
