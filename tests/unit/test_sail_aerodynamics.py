"""Unit tests for multi-sail 3D aerodynamics, Center of Effort kinematics, and rig interactions."""

from __future__ import annotations

import math

from sia_sim.physics.sails.polars import SailType, evaluate_sail_polar
from sia_sim.physics.sails.rig import (
    ApparentWindFeedbackHook,
    HullHydrodynamicsHook,
    SailTrimProfileHook,
    WaveSailInteractionHook,
    create_standard_sloop_rig,
)


class TestSailPolars:
    def test_mainsail_polar_attached_flow(self) -> None:
        polar = evaluate_sail_polar(SailType.MAINSAIL, alpha_deg=15.0, camber_ratio=0.12)
        assert polar.cl > 1.0
        assert polar.cd < 0.3
        assert not polar.is_stalled

    def test_mainsail_polar_stall_at_high_alpha(self) -> None:
        polar = evaluate_sail_polar(SailType.MAINSAIL, alpha_deg=45.0, camber_ratio=0.12)
        assert polar.is_stalled
        assert polar.cd > 0.8

    def test_spinnaker_polar_high_drag_at_deep_angles(self) -> None:
        polar = evaluate_sail_polar(SailType.SPINNAKER, alpha_deg=75.0, camber_ratio=0.22)
        assert polar.cd > 1.2


class TestSailKinematicsAndForces:
    def test_boom_angle_eases_with_sheet(self) -> None:
        rig = create_standard_sloop_rig()
        main = rig.get_sail("mainsail")
        assert main is not None

        # Head to wind (AWA = 0°): fully sheeted in -> boom is on centerline
        main.sheet_trim_ratio = 1.0
        boom_head_wind = main.calculate_boom_angle(awa_deg=0.0)
        assert math.isclose(boom_head_wind, 0.0, abs_tol=1e-3)

        # On reach (AWA = 60°), easing sheet pushes boom further out to leeward
        main.sheet_trim_ratio = 1.0
        boom_reach_trimmed = main.calculate_boom_angle(awa_deg=60.0)
        main.sheet_trim_ratio = 0.20
        boom_reach_eased = main.calculate_boom_angle(awa_deg=60.0)

        assert abs(boom_reach_eased) > abs(boom_reach_trimmed)
        assert boom_reach_eased < 0.0  # Starboard wind pushes boom to port (-y -> negative angle)

    def test_center_of_effort_shifts_outboard_when_boom_eased(self) -> None:
        rig = create_standard_sloop_rig()
        main = rig.get_sail("mainsail")
        assert main is not None

        coe_trimmed = main.compute_center_of_effort(boom_angle_deg=0.0, reefed_ratio=1.0)
        coe_eased = main.compute_center_of_effort(boom_angle_deg=-45.0, reefed_ratio=1.0)

        # Centerline when trimmed (y ~ 0)
        assert math.isclose(coe_trimmed[1], 0.0, abs_tol=1e-3)
        # Shifted to port (-y) when boom eased
        assert coe_eased[1] < -0.5

    def test_reefing_lowers_vertical_center_of_effort(self) -> None:
        rig = create_standard_sloop_rig()
        main = rig.get_sail("mainsail")
        assert main is not None

        coe_full = main.compute_center_of_effort(boom_angle_deg=0.0, reefed_ratio=1.0)
        coe_reef2 = main.compute_center_of_effort(boom_angle_deg=0.0, reefed_ratio=0.55)

        # z_CoE drops significantly with reefing
        assert coe_reef2[2] < coe_full[2] - 1.5


class TestRigInteractionsAndMoments:
    def test_downwind_blanketing_on_dead_run(self) -> None:
        rig = create_standard_sloop_rig()
        # On TWA 180°, headsail should be blanketed by mainsail
        blanket_map, _ = rig.evaluate_interactions(awa_deg=180.0)
        assert blanket_map["headsail"] > 0.70
        assert blanket_map["mainsail"] == 0.0

    def test_upwind_slot_effect_enhances_mainsail_lift(self) -> None:
        rig = create_standard_sloop_rig()
        # On TWA 45° (close hauled / close reach), slot effect accelerates flow over main
        _, slot_map = rig.evaluate_interactions(awa_deg=45.0)
        assert slot_map["mainsail"] > 0.05

    def test_rig_evaluation_produces_3d_forces_and_moments(self) -> None:
        rig = create_standard_sloop_rig(mainsail_area_m2=45.0, headsail_area_m2=45.0)
        res = rig.evaluate(aws_m_s=10.0, awa_deg=60.0, heel_deg=15.0, mainsheet_pct=90.0)

        assert res.thrust_n > 500.0  # positive forward drive
        assert res.side_force_n < -500.0  # starboard wind pushes vessel to port (-y)
        assert res.heeling_moment_nm > 2000.0  # heeling moment rolling vessel to starboard
        assert len(res.sail_results) == 5

    def test_set_sail_plan_presets(self) -> None:
        rig = create_standard_sloop_rig()
        main = rig.get_sail("mainsail")
        headsail = rig.get_sail("headsail")
        storm = rig.get_sail("storm_jib")
        assert main is not None and headsail is not None and storm is not None

        # Test REEF_2
        rig.set_sail_plan("REEF_2")
        assert main.is_active and math.isclose(main.reefed_ratio, 0.55)
        assert headsail.is_active and math.isclose(headsail.reefed_ratio, 0.65)
        assert not storm.is_active

        # Test STORM_JIB_ONLY
        rig.set_sail_plan("STORM_JIB_ONLY")
        assert not main.is_active
        assert storm.is_active

        # Test BARE_POLES
        rig.set_sail_plan("BARE_POLES")
        assert not main.is_active and not headsail.is_active and not storm.is_active


class TestExtensibilityHooks:
    def test_protocol_compliance_and_hooks_assignment(self) -> None:
        rig = create_standard_sloop_rig()

        class MockHydrodynamics:
            def compute_hydrodynamic_forces(
                self,
                u_m_s: float,
                v_m_s: float,
                yaw_rate_rad_s: float,
                heel_deg: float,
                leeway_angle_deg: float,
            ) -> tuple[float, float, float]:
                return (-100.0, 500.0, -50.0)

        class MockApparentWind:
            def compute_local_apparent_wind(
                self,
                true_wind_speed_m_s: float,
                true_wind_angle_deg: float,
                vessel_speed_m_s: float,
                roll_rate_rad_s: float,
                pitch_rate_rad_s: float,
                z_height_m: float,
            ) -> tuple[float, float]:
                return (true_wind_speed_m_s * 1.1, true_wind_angle_deg - 5.0)

        class MockWaveSail:
            def compute_wave_wind_attenuation(
                self,
                wave_height_m: float,
                relative_wave_position: float,
                nominal_aws_m_s: float,
            ) -> float:
                return 0.85

        class MockTrimProfile:
            def compute_twist_angle_deg(
                self,
                vang_tension_ratio: float,
                mainsheet_tension_ratio: float,
                z_relative: float,
            ) -> float:
                return 3.5

        mock_hydro = MockHydrodynamics()
        mock_wind = MockApparentWind()
        mock_wave = MockWaveSail()
        mock_trim = MockTrimProfile()

        assert isinstance(mock_hydro, HullHydrodynamicsHook)
        assert isinstance(mock_wind, ApparentWindFeedbackHook)
        assert isinstance(mock_wave, WaveSailInteractionHook)
        assert isinstance(mock_trim, SailTrimProfileHook)

        rig.hydrodynamics_hook = mock_hydro
        rig.apparent_wind_hook = mock_wind
        rig.wave_sail_hook = mock_wave
        rig.trim_profile_hook = mock_trim

        assert rig.hydrodynamics_hook is mock_hydro
        assert rig.apparent_wind_hook is mock_wind
        assert rig.wave_sail_hook is mock_wave
        assert rig.trim_profile_hook is mock_trim
