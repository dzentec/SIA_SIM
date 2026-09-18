"""Unit tests for Phase 12 Rig & Sails Data Contracts and Enums."""

import pytest
from pydantic import ValidationError

from sia_sim.contracts.sails import (
    FurlerState,
    RigState,
    RopeControlInput,
    RopeState,
    RopeStatus,
    SailState,
    SailStatus,
    TravelerControlInput,
    TravelerState,
)


def test_rope_status_and_sail_status_separation() -> None:
    """Rope and Sail statuses must be distinct enums."""
    assert RopeStatus.OK == "OK"
    assert RopeStatus.OVERLOAD == "OVERLOAD"
    assert RopeStatus.BROKEN == "BROKEN"
    assert RopeStatus.CLAMPED == "CLAMPED"
    assert RopeStatus.SLACK == "SLACK"
    assert RopeStatus.TAUT == "TAUT"

    assert SailStatus.OK == "OK"
    assert SailStatus.LUFFING == "LUFFING"
    assert SailStatus.STALL == "STALL"
    assert SailStatus.ATTACHED == "ATTACHED"
    assert SailStatus.FURLED == "FURLED"

    # Enums must not contain cross-domain values
    assert not hasattr(RopeStatus, "LUFFING")
    assert not hasattr(SailStatus, "CLAMPED")


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
