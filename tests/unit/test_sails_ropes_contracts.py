"""Unit tests for Phase 12 Rig & Sails Data Contracts, Status Model and Enums."""

import pytest
from pydantic import ValidationError

from sia_sim.contracts.sails import (
    ClampState,
    FurlerState,
    RigState,
    RopeControlInput,
    RopeLoadStatus,
    RopeState,
    RopeStatus,
    SailState,
    SailStatus,
    TravelerControlInput,
    TravelerState,
    compute_load_status,
)


def test_rope_status_and_sail_status_separation() -> None:
    """Rope load and clamp statuses must be distinct enums."""
    assert RopeLoadStatus.OK == "OK"
    assert RopeLoadStatus.OVERLOAD == "OVERLOAD"
    assert RopeLoadStatus.BROKEN == "BROKEN"
    assert RopeLoadStatus.SLACK == "SLACK"
    assert RopeLoadStatus.TAUT == "TAUT"
    # CLAMPED is removed from RopeLoadStatus
    assert not hasattr(RopeLoadStatus, "CLAMPED")

    assert ClampState.CLAMPED == "CLAMPED"
    assert ClampState.UNCLAMPED == "UNCLAMPED"

    assert SailStatus.OK == "OK"
    assert SailStatus.LUFFING == "LUFFING"
    assert SailStatus.STALL == "STALL"
    assert SailStatus.ATTACHED == "ATTACHED"
    assert SailStatus.FURLED == "FURLED"

    # Enums must not contain cross-domain values
    assert not hasattr(RopeLoadStatus, "LUFFING")
    assert not hasattr(SailStatus, "CLAMPED")


def test_compute_load_status_priority_order() -> None:
    """Verify strictly prioritized order: BROKEN > OVERLOAD > TAUT > SLACK > OK."""
    # 1. Broken threshold overrides everything
    assert (
        compute_load_status(
            tension_n=5000.0,
            slack_threshold_n=100.0,
            taut_threshold_n=2000.0,
            max_working_load_n=2500.0,
            breaking_load_n=5000.0,
        )
        == RopeLoadStatus.BROKEN
    )

    # 2. Overload
    assert (
        compute_load_status(
            tension_n=2600.0,
            slack_threshold_n=100.0,
            taut_threshold_n=2000.0,
            max_working_load_n=2500.0,
            breaking_load_n=5000.0,
        )
        == RopeLoadStatus.OVERLOAD
    )

    # 3. Taut
    assert (
        compute_load_status(
            tension_n=2100.0,
            slack_threshold_n=100.0,
            taut_threshold_n=2000.0,
            max_working_load_n=2500.0,
            breaking_load_n=5000.0,
        )
        == RopeLoadStatus.TAUT
    )

    # 4. Slack
    assert (
        compute_load_status(
            tension_n=50.0,
            slack_threshold_n=100.0,
            taut_threshold_n=2000.0,
            max_working_load_n=2500.0,
            breaking_load_n=5000.0,
        )
        == RopeLoadStatus.SLACK
    )

    # 5. OK
    assert (
        compute_load_status(
            tension_n=500.0,
            slack_threshold_n=100.0,
            taut_threshold_n=2000.0,
            max_working_load_n=2500.0,
            breaking_load_n=5000.0,
        )
        == RopeLoadStatus.OK
    )


def test_slack_threshold_from_contract() -> None:
    """Slack threshold is channel-dependent (not a hardcoded constant)."""
    light_line_slack = compute_load_status(
        tension_n=70.0,
        slack_threshold_n=50.0,  # line with 50N threshold is OK at 70N
        taut_threshold_n=1000.0,
        max_working_load_n=1200.0,
        breaking_load_n=2500.0,
    )
    assert light_line_slack == RopeLoadStatus.OK

    heavy_line_slack = compute_load_status(
        tension_n=70.0,
        slack_threshold_n=150.0,  # line with 150N threshold is SLACK at 70N
        taut_threshold_n=2100.0,
        max_working_load_n=2500.0,
        breaking_load_n=5500.0,
    )
    assert heavy_line_slack == RopeLoadStatus.SLACK


def test_broken_overrides_overload() -> None:
    """When tension exceeds breaking_load_n, status is BROKEN, not OVERLOAD."""
    stat = compute_load_status(
        tension_n=6000.0,
        slack_threshold_n=100.0,
        taut_threshold_n=2000.0,
        max_working_load_n=2500.0,
        breaking_load_n=5000.0,
    )
    assert stat == RopeLoadStatus.BROKEN


def test_taut_threshold_per_channel() -> None:
    """TAUT status begins strictly at channel's taut_threshold_n."""
    stat_below = compute_load_status(
        tension_n=1450.0,
        slack_threshold_n=100.0,
        taut_threshold_n=1500.0,
        max_working_load_n=1800.0,
        breaking_load_n=4000.0,
    )
    assert stat_below == RopeLoadStatus.OK

    stat_at = compute_load_status(
        tension_n=1500.0,
        slack_threshold_n=100.0,
        taut_threshold_n=1500.0,
        max_working_load_n=1800.0,
        breaking_load_n=4000.0,
    )
    assert stat_at == RopeLoadStatus.TAUT


def test_rope_control_input_validation() -> None:
    """Validates boundary constraints on RopeControlInput."""
    valid = RopeControlInput(rope_id="mainsheet", target_trim=0.75, clamped=True)
    assert valid.rope_id == "mainsheet"
    assert valid.target_trim == 0.75
    assert valid.clamped is True

    # Out of bounds target_trim
    with pytest.raises(ValidationError):
        RopeControlInput(rope_id="mainsheet", target_trim=1.5, clamped=False)

    with pytest.raises(ValidationError):
        RopeControlInput(rope_id="mainsheet", target_trim=-0.1, clamped=False)


def test_traveler_signed_range_contract() -> None:
    """Traveler must support signed range [-1.0, 1.0]."""
    t_input = TravelerControlInput(traveler_id="traveler", target_pos=-0.8, clamped=False)
    assert t_input.target_pos == -0.8

    t_state = TravelerState(
        id="traveler",
        target_pos=0.5,
        actual_pos=0.48,
        speed_m_s=0.02,
        clamped=True,
        status=RopeStatus.OK,
    )
    assert t_state.actual_pos == 0.48

    # Invalid positions > 1.0 or < -1.0
    with pytest.raises(ValidationError):
        TravelerControlInput(target_pos=1.2, clamped=False)

    with pytest.raises(ValidationError):
        TravelerState(
            id="traveler",
            target_pos=-1.5,
            actual_pos=0.0,
            speed_m_s=0.0,
            clamped=False,
            status=RopeStatus.OK,
        )


def test_furler_state_contract() -> None:
    """FurlerState tracks line_trim, drum_turns, furled_ratio, and area_ratio."""
    furler = FurlerState(
        id="jib_furler",
        line_trim=0.3,
        line_length_m=4.5,
        drum_turns=15.0,
        furled_ratio=0.3,
        area_ratio=0.7,
        status=RopeStatus.OK,
    )
    assert furler.area_ratio == 0.7
    assert furler.furled_ratio == 0.3


def test_rig_state_aggregation_and_serialization() -> None:
    """RigState serializes full telemetry snapshot to dictionary."""
    rope = RopeState(
        id="mainsheet",
        side="starboard",
        group="main",
        target_trim=0.5,
        actual_trim=0.5,
        clamped=True,
        length_m=5.0,
        speed_m_s=0.0,
        tension_n=1200.0,
        max_working_load_n=2500.0,
        breaking_load_n=5000.0,
        status=RopeStatus.OK,
    )
    traveler = TravelerState(
        id="traveler",
        target_pos=0.0,
        actual_pos=0.0,
        speed_m_s=0.0,
        clamped=True,
        status=RopeStatus.OK,
    )
    furler = FurlerState(
        id="jib_furler",
        line_trim=0.0,
        line_length_m=0.0,
        drum_turns=0.0,
        furled_ratio=0.0,
        area_ratio=1.0,
        status=RopeStatus.OK,
    )
    sail = SailState(
        sail_id="mainsail",
        effective_area_m2=35.0,
        area_ratio=1.0,
        angle_of_attack_deg=12.5,
        twist_deg=4.0,
        camber_ratio=0.12,
        lift_force_n=1500.0,
        drag_force_n=300.0,
        center_of_effort_z=5.2,
        reef_level=0,
        status=SailStatus.OK,
    )

    rig = RigState(
        timestamp_ms=1726690000000,
        ropes={"mainsheet": rope},
        traveler=traveler,
        furler=furler,
        sails={"mainsail": sail},
        wind={"awa_deg": 35.0, "aws_kt": 15.0},
    )

    data = rig.model_dump()
    assert data["timestamp_ms"] == 1726690000000
    assert data["ropes"]["mainsheet"]["status"] == "OK"
    assert data["sails"]["mainsail"]["status"] == "OK"
    assert data["traveler"]["actual_pos"] == 0.0
