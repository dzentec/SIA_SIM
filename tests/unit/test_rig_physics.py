"""Unit tests for Phase 12 Rig Kinematics, Winch Inertia & Clutch/Stopper Physics Engine."""

from sia_sim.contracts.sails import RopeStatus, SailStatus
from sia_sim.physics.sails.rig import (
    FurlerModel,
    TravelerModel,
    WinchModel,
    create_default_rig_control_system,
)
from sia_sim.physics.sails.sail import Sail, SailConfig, SailType


def test_winch_rate_limit_and_inertia() -> None:
    """Winch actual_trim must advance smoothly bounded by rate limit and acceleration."""
    winch = WinchModel(
        id="mainsheet",
        side="starboard",
        group="main",
        max_length_m=10.0,
        v_winch_max_m_s=0.5,
        a_winch_max_m_s2=2.0,
        actual_trim=0.0,
        target_trim=1.0,
        clamped=False,
    )

    # First small step (dt = 0.1s)
    state_1 = winch.step(target_trim=1.0, clamped=False, external_tension_n=100.0, dt=0.1)
    assert state_1.actual_trim > 0.0
    assert state_1.actual_trim < 1.0
    assert state_1.speed_m_s > 0.0

    # Accelerating towards max speed (10 seconds total at 0.5 m/s = 5m / 10m = 0.5 trim)
    prev_trim = state_1.actual_trim
    for _ in range(120):
        s = winch.step(target_trim=1.0, clamped=False, external_tension_n=100.0, dt=0.1)
        assert s.actual_trim >= prev_trim
        prev_trim = s.actual_trim

    assert winch.actual_trim > 0.5


def test_winch_load_factor_slowdown() -> None:
    """Winch hauling speed must decrease when tension approaches SWL (Safe Working Load)."""
    winch_light = WinchModel(
        id="mainsheet",
        side="starboard",
        group="main",
        max_working_load_n=2000.0,
        actual_trim=0.0,
        target_trim=1.0,
        clamped=False,
    )
    winch_heavy = WinchModel(
        id="mainsheet",
        side="starboard",
        group="main",
        max_working_load_n=2000.0,
        actual_trim=0.0,
        target_trim=1.0,
        clamped=False,
    )

    # 1.0s under low tension (100 N) vs high tension (1800 N)
    s_light = winch_light.step(target_trim=1.0, clamped=False, external_tension_n=100.0, dt=1.0)
    s_heavy = winch_heavy.step(target_trim=1.0, clamped=False, external_tension_n=1800.0, dt=1.0)

    assert s_light.actual_trim > s_heavy.actual_trim
    assert s_light.speed_m_s > s_heavy.speed_m_s


def test_clutch_lock_freezes_trim_while_tension_grows() -> None:
    """When clamped=True, actual_trim is locked, but tension and status reflect loads."""
    winch = WinchModel(
        id="mainsheet",
        side="starboard",
        group="main",
        actual_trim=0.5,
        target_trim=1.0,
        clamped=True,
        slack_threshold_n=100.0,
        taut_threshold_n=1600.0,
        max_working_load_n=2000.0,
        breaking_load_n=4000.0,
    )

    # Step with target=1.0 but clamped=True -> trim unchanged, status is OK (500N in safe band)
    s1 = winch.step(target_trim=1.0, clamped=True, external_tension_n=500.0, dt=0.5)
    assert s1.actual_trim == 0.5
    assert s1.clamped is True
    assert s1.status == RopeStatus.OK

    # Higher load -> OVERLOAD while still clamped
    s2 = winch.step(target_trim=1.0, clamped=True, external_tension_n=2500.0, dt=0.5)
    assert s2.actual_trim == 0.5
    assert s2.clamped is True
    assert s2.status == RopeStatus.OVERLOAD

    # Breaking load -> BROKEN
    s3 = winch.step(target_trim=1.0, clamped=True, external_tension_n=4500.0, dt=0.5)
    assert s3.status == RopeStatus.BROKEN


def test_traveler_signed_movement() -> None:
    """Traveler moves within signed [-1.0 ... +1.0] range when unclamped."""
    traveler = TravelerModel(id="traveler", target_pos=0.0, actual_pos=0.0, clamped=True)

    # Clamped: does not move
    s_clamped = traveler.step(target_pos=-0.8, clamped=True, dt=0.5)
    assert s_clamped.actual_pos == 0.0
    assert s_clamped.clamped is True
    assert s_clamped.status == RopeStatus.OK

    # Unclamped: travels towards port (-0.8)
    s_unclamped = traveler.step(target_pos=-0.8, clamped=False, dt=1.0)
    assert s_unclamped.actual_pos < 0.0
    assert s_unclamped.actual_pos >= -0.8
    assert s_unclamped.clamped is False
    assert s_unclamped.status == RopeStatus.OK


def test_furler_kinematics_and_penalty() -> None:
    """Furler drum converts line_trim to furled_ratio and area_ratio."""
    furler = FurlerModel(
        id="jib_furler",
        drum_circumference_m=0.4,
        furling_pitch_m=0.25,
        luff_length_m=12.5,
        max_furling_line_m=20.0,
    )

    # Line eased (trim = 0.0) -> full sail area
    s_open = furler.step(line_trim=0.0, clamped=True, dt=0.1)
    assert s_open.furled_ratio == 0.0
    assert s_open.area_ratio == 1.0

    # Line hauled (trim = 0.5) -> half furled
    s_mid = furler.step(line_trim=0.5, clamped=True, dt=0.1)
    assert s_mid.furled_ratio > 0.0
    assert s_mid.area_ratio < 1.0
    assert abs(s_mid.furled_ratio + s_mid.area_ratio - 1.0) < 1e-5


def test_aerodynamic_trim_effects_and_statuses() -> None:
    """Boom Vang alters twist, Cunningham shifts stall angle, Outhaul alters camber."""
    cfg = SailConfig(
        sail_id="mainsail",
        sail_type=SailType.MAINSAIL,
        nominal_area_m2=45.0,
        tack_point=(0.0, 0.0, 0.8),
        head_point=(0.0, 0.0, 16.0),
        clew_base_point=(-4.5, 0.0, 0.8),
        foot_length_m=4.5,
        luff_length_m=15.2,
        camber_ratio=0.12,
        stall_angle_base_deg=16.0,
        luffing_threshold_deg=3.0,
    )
    sail = Sail(cfg)

    # 1. Full vang (twist_trim = 1.0) vs loose vang (twist_trim = 0.0)
    sail.twist_trim = 1.0
    res_tight = sail.evaluate(aws_m_s=8.0, awa_deg=45.0)
    assert res_tight.twist_deg == 0.0

    sail.twist_trim = 0.0
    res_loose = sail.evaluate(aws_m_s=8.0, awa_deg=45.0)
    assert res_loose.twist_deg == 12.0
    # Higher twist gives higher CoE z
    assert res_loose.coe[2] > res_tight.coe[2]

    # 2. Status check: luffing at low AoA
    res_luff = sail.evaluate(aws_m_s=8.0, awa_deg=2.0)
    assert res_luff.status == SailStatus.LUFFING


def test_rig_control_system_step_integration() -> None:
    """Full RigControlSystem steps all lines and produces valid RigState."""
    sys = create_default_rig_control_system()

    # Step simulation with 15 knots (7.7 m/s) apparent wind at 40° AWA
    forces, state = sys.step(
        timestamp_ms=1726690000000,
        dt=0.01,  # 100 Hz tick
        aws_m_s=7.7,
        awa_deg=40.0,
        heel_deg=12.0,
    )

    assert forces.thrust_n > 0.0
    assert "mainsheet" in state.ropes
    assert "jib_sheet_port" in state.ropes
    assert "reef_line_1" in state.ropes
    assert "reef_line_2" in state.ropes
    assert "reef_line_3" in state.ropes
    assert "traveler" == state.traveler.id
    assert "jib_furler" == state.furler.id
    assert state.sails["mainsail"].status in (SailStatus.OK, SailStatus.ATTACHED, SailStatus.STALL)


def test_rig_controller_reef_3_preset() -> None:
    """Reef 3 preset tightens reef_line_3, drops halyard to 0.25, and reduces area to ~35%."""
    from sia_sim.engine.rig_controller import RigController

    controller = RigController()
    # Ease mainsheet to pass reefing interlock
    controller.rig_system.winches["mainsheet"].actual_trim = 0.20

    res = controller.execute_preset({"preset": "REEF_3", "timestamp_ms": 1726690000000})

    assert res["status"] == "ACCEPTED"
    assert res["reef_level"] == 3
    assert res["expected_area_ratio"] == 0.35
    assert controller.active_preset == "REEF_3"

    # Verify rope settings applied to rig_system
    rig_sys = controller.rig_system
    assert rig_sys.winches["reef_line_3"].target_trim == 1.0
    assert rig_sys.winches["main_halyard"].target_trim == 0.25
    assert rig_sys.winches["main_halyard"].clamped is True


