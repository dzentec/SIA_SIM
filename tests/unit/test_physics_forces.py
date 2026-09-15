"""Unit tests for aerodynamic, hydrodynamic, and hydrostatic force calculations."""

from __future__ import annotations

import math

from sia_sim.physics.forces import (
    apparent_wind,
    righting_moment,
    rudder_forces,
    sail_forces,
)


class TestApparentWind:
    def test_headwind_speed_adds(self) -> None:
        # Moving North at 5 m/s directly into North wind at 10 m/s
        aws, awa = apparent_wind(
            u_m_s=5.0,
            v_m_s=0.0,
            heading_deg=0.0,
            tws_m_s=10.0,
            twa_deg=0.0,
        )
        assert math.isclose(aws, 15.0, rel_tol=1e-3)
        assert math.isclose(abs(awa), 0.0, abs_tol=1e-3)

    def test_beam_reach_geometry(self) -> None:
        # Moving North at 6 m/s, wind from East (90 deg) at 8 m/s
        aws, awa = apparent_wind(
            u_m_s=6.0,
            v_m_s=0.0,
            heading_deg=0.0,
            tws_m_s=8.0,
            twa_deg=90.0,
        )
        # Expected AWS = sqrt(6^2 + 8^2) = 10.0 m/s
        assert math.isclose(aws, 10.0, rel_tol=1e-3)
        # Expected AWA = atan2(8, 6) approx 53.13 deg (wind pulled forward towards bow)
        assert math.isclose(awa, 53.13, abs_tol=0.1)


class TestSailForces:
    def test_zero_wind_produces_zero_force(self) -> None:
        thrust, side, roll_m, yaw_m = sail_forces(aws_m_s=0.0, awa_deg=45.0)
        assert thrust == 0.0
        assert side == 0.0
        assert roll_m == 0.0
        assert yaw_m == 0.0

    def test_beam_reach_produces_positive_thrust_and_heel(self) -> None:
        thrust, _side, roll_m, _yaw_m = sail_forces(
            aws_m_s=10.0,
            awa_deg=60.0,
            mainsheet_pct=100.0,
        )
        assert thrust > 0.0
        # Wind from starboard (awa > 0) produces roll moment
        assert roll_m != 0.0


class TestRudderForces:
    def test_neutral_rudder_zero_yaw_moment(self) -> None:
        y_rud, n_rud = rudder_forces(
            u_m_s=3.0,
            v_m_s=0.0,
            r_rad_s=0.0,
            rudder_angle_deg=0.0,
            heel_deg=0.0,
        )
        assert math.isclose(y_rud, 0.0, abs_tol=1e-3)
        assert math.isclose(n_rud, 0.0, abs_tol=1e-3)

    def test_starboard_rudder_turns_vessel(self) -> None:
        y_rud, n_rud = rudder_forces(
            u_m_s=3.0,
            v_m_s=0.0,
            r_rad_s=0.0,
            rudder_angle_deg=10.0,
            heel_deg=0.0,
        )
        assert y_rud > 0.0
        assert n_rud < 0.0  # Rudder aft creates negative yaw moment for +rudder

    def test_high_heel_reduces_rudder_effectiveness(self) -> None:
        # Upright
        _, n_upright = rudder_forces(
            u_m_s=3.0,
            v_m_s=0.0,
            r_rad_s=0.0,
            rudder_angle_deg=15.0,
            heel_deg=0.0,
        )
        # Severe heel (35 deg)
        _, n_heeled = rudder_forces(
            u_m_s=3.0,
            v_m_s=0.0,
            r_rad_s=0.0,
            rudder_angle_deg=15.0,
            heel_deg=35.0,
        )
        assert abs(n_heeled) < 0.4 * abs(n_upright)


class TestRightingMoment:
    def test_zero_heel_zero_righting_moment(self) -> None:
        k_rm = righting_moment(0.0)
        assert math.isclose(k_rm, 0.0, abs_tol=1e-3)

    def test_heel_produces_restoring_moment(self) -> None:
        # Positive heel (+starboard) produces negative restoring moment
        k_rm = righting_moment(20.0, mass_kg=4500.0, gm_m=1.1)
        assert k_rm < 0.0
